"""Canonical model-provider metadata, validation, and safe error messages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from openjiuwen.core.foundation.llm.schema.config import ProviderType

from jiuwenswarm.common.model_config_validation import is_valid_api_base

ProviderTransport = Literal["native", "openai_compatible", "anthropic", "gemini"]


class ModelConfigurationError(ValueError):
    """A user-actionable error in one model configuration entry."""


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    transport: ProviderTransport
    default_api_base: str
    requires_api_key: bool = True
    requires_api_base: bool = True


@dataclass(frozen=True)
class ValidatedModelConnection:
    provider: str
    api_base: str
    api_key: str
    model_name: str


@dataclass(frozen=True)
class ClassifiedModelError:
    code: str
    message: str


_EXPLICIT_SPECS = {
    "OpenAI": ProviderSpec("OpenAI", "native", "https://api.openai.com/v1"),
    "OpenAIAccount": ProviderSpec(
        "OpenAIAccount",
        "native",
        "https://chatgpt.com/backend-api/codex",
        requires_api_key=False,
    ),
    "OpenAICompatible": ProviderSpec(
        "OpenAICompatible", "openai_compatible", ""
    ),
    "OpenRouter": ProviderSpec(
        "OpenRouter", "native", "https://openrouter.ai/api/v1"
    ),
    "Anthropic": ProviderSpec(
        "Anthropic", "anthropic", "https://api.anthropic.com"
    ),
    "Gemini": ProviderSpec(
        "Gemini", "gemini", "https://generativelanguage.googleapis.com"
    ),
    "DashScope": ProviderSpec(
        "DashScope",
        "native",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "DeepSeek": ProviderSpec("DeepSeek", "native", "https://api.deepseek.com"),
    "SiliconFlow": ProviderSpec(
        "SiliconFlow", "native", "https://api.siliconflow.cn/v1"
    ),
}


def _build_specs() -> dict[str, ProviderSpec]:
    specs = dict(_EXPLICIT_SPECS)
    for provider in ProviderType:
        specs.setdefault(provider.value, ProviderSpec(provider.value, "native", ""))
    return specs


SUPPORTED_MODEL_PROVIDERS = _build_specs()

_ALIASES = {
    "openai-compatible": "OpenAICompatible",
    "openai_compatible": "OpenAICompatible",
    "openaicompatible": "OpenAICompatible",
    "compatible": "OpenAICompatible",
    "claude": "Anthropic",
    "google": "Gemini",
    "google-gemini": "Gemini",
    "google_gemini": "Gemini",
}
for _canonical_name in SUPPORTED_MODEL_PROVIDERS:
    _ALIASES.setdefault(_canonical_name.lower(), _canonical_name)


def normalize_model_provider(provider: str) -> str:
    """Return a canonical provider name without looking at the model name."""
    value = str(provider or "").strip()
    return _ALIASES.get(value.lower(), value)


def list_model_providers() -> list[str]:
    """List every provider accepted by JiuwenSwarm configuration surfaces."""
    return list(SUPPORTED_MODEL_PROVIDERS)


def get_provider_spec(provider: str) -> ProviderSpec:
    canonical = normalize_model_provider(provider)
    try:
        return SUPPORTED_MODEL_PROVIDERS[canonical]
    except KeyError as exc:
        available = ", ".join(list_model_providers())
        raise ModelConfigurationError(
            f"Unsupported model provider '{canonical or '<empty>'}'. Available providers: {available}"
        ) from exc


def validate_model_connection_config(
    provider: str,
    api_base: str,
    api_key: str,
    model_name: str,
) -> ValidatedModelConnection:
    """Validate and normalize the four fields that determine model routing."""
    spec = get_provider_spec(provider)
    base = str(api_base or "").strip().rstrip("/")
    key = str(api_key or "").strip()
    model = str(model_name or "").strip()

    if not model:
        raise ModelConfigurationError(f"A model name is required for provider {spec.name}.")
    if spec.requires_api_key and not key:
        raise ModelConfigurationError(f"An API key is required for provider {spec.name}.")
    if spec.requires_api_base and not is_valid_api_base(base):
        raise ModelConfigurationError(
            f"Base URL for provider {spec.name} must be a non-placeholder absolute HTTP(S) URL."
        )
    return ValidatedModelConnection(spec.name, base, key, model)


_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(sk-[A-Za-z0-9_-]{4,})\b"),
    re.compile(r"(?i)(api[_ -]?key\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+"),
)


def _safe_error_text(error: BaseException) -> str:
    text = str(error).strip() or error.__class__.__name__
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(
            lambda match: (match.group(1) if match.lastindex else "") + "[REDACTED]",
            text,
        )
    return text


def classify_model_error(error: BaseException) -> ClassifiedModelError:
    """Classify an upstream/client error into a stable, secret-safe category."""
    message = _safe_error_text(error)
    lower = message.lower()
    if any(token in lower for token in ("401", "403", "invalid api key", "authentication", "unauthorized")):
        code = "AUTH_ERROR"
    elif any(token in lower for token in ("model_not_found", "model not found", "unknown model", "invalid model")):
        code = "MODEL_NOT_FOUND"
    elif any(token in lower for token in ("429", "rate limit", "too many requests")):
        code = "RATE_LIMITED"
    elif any(
        token in lower
        for token in (
            "certificate",
            "ssl",
            "tls",
            "connection",
            "connecterror",
            "dns",
            "name resolution",
            "invalid url",
        )
    ):
        code = "CONNECTION_ERROR"
    elif any(token in lower for token in ("unsupported", "unavailable model provider", "client_provider")):
        code = "PROVIDER_ERROR"
    else:
        code = "LLM_ERROR"
    return ClassifiedModelError(code=code, message=message)


__all__ = [
    "ClassifiedModelError",
    "ModelConfigurationError",
    "ProviderSpec",
    "SUPPORTED_MODEL_PROVIDERS",
    "ValidatedModelConnection",
    "classify_model_error",
    "get_provider_spec",
    "list_model_providers",
    "normalize_model_provider",
    "validate_model_connection_config",
]
