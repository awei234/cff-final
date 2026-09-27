"""Explicit, secret-safe provider runtime configuration."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


REQUIRED_FIELDS = {"api_base", "model_id", "api_key_env"}


class ProviderConfigError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ResolvedProvider:
    provider: str
    api_base: str
    model_id: str
    api_key_env: str
    api_key_present: bool

    def as_report(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "api_base": self.api_base,
            "model_id": self.model_id,
            "api_key_source": f"env:{self.api_key_env}",
            "api_key_present": self.api_key_present,
        }

    def load_api_key(self, environ: Mapping[str, str] | None = None) -> str:
        value = (environ if environ is not None else os.environ).get(self.api_key_env, "")
        if not value.strip():
            raise ProviderConfigError(
                "api_key_missing",
                f"required environment variable is missing: {self.api_key_env}",
            )
        return value


def _read_config(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise ProviderConfigError("provider_config_missing", f"provider configuration does not exist: {path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProviderConfigError("provider_config_invalid_json", f"invalid provider JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ProviderConfigError("provider_config_invalid_type", "provider configuration must be an object")
    normalized: dict[str, dict[str, str]] = {}
    for name, raw in parsed.items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            raise ProviderConfigError("provider_config_invalid_entry", "each provider entry must be an object")
        if set(raw) != REQUIRED_FIELDS:
            raise ProviderConfigError("provider_config_invalid_fields", f"invalid fields for provider: {name}")
        if any(not isinstance(raw[field], str) or not raw[field].strip() for field in REQUIRED_FIELDS):
            raise ProviderConfigError("provider_config_invalid_value", f"provider fields must be non-empty strings: {name}")
        normalized[name.lower()] = {field: raw[field].strip() for field in REQUIRED_FIELDS}
    return normalized


def resolve_provider(
    *,
    provider: str,
    config_path: str | Path,
    api_base: str | None = None,
    model_id: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> ResolvedProvider:
    provider_name = provider.strip().lower()
    config = _read_config(Path(config_path))
    if provider_name not in config:
        raise ProviderConfigError("provider_unknown", f"unknown provider: {provider_name}")
    entry = config[provider_name]
    selected_base = (api_base or entry["api_base"]).rstrip("/")
    selected_model = model_id or entry["model_id"]
    parsed_url = urlparse(selected_base)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ProviderConfigError("api_base_invalid", f"provider API base must be an HTTPS URL: {provider_name}")
    if not selected_model.strip():
        raise ProviderConfigError("model_id_missing", f"model ID is empty: {provider_name}")
    env = environ if environ is not None else os.environ
    key_env = entry["api_key_env"]
    return ResolvedProvider(
        provider=provider_name,
        api_base=selected_base,
        model_id=selected_model.strip(),
        api_key_env=key_env,
        api_key_present=bool(env.get(key_env, "").strip()),
    )

