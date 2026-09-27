"""Minimal OpenAI-compatible live verification with sanitized evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Callable
import urllib.error
import urllib.request

from .providers import ResolvedProvider


class SmokeError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def run_live_smoke(
    provider: ResolvedProvider,
    api_key: str,
    *,
    opener: Callable[..., object] = urllib.request.urlopen,
    timeout_seconds: int = 30,
) -> dict[str, object]:
    payload = {
        "model": provider.model_id,
        "messages": [{"role": "user", "content": "Reply with OK only."}],
        "temperature": 0,
        "max_tokens": 2,
    }
    request = urllib.request.Request(
        provider.api_base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with opener(request, timeout=timeout_seconds) as response:
            response_body = response.read()
            http_status = int(response.status)
            request_id = response.headers.get("x-request-id") or response.headers.get("x-requestid")
    except urllib.error.HTTPError as exc:
        raise SmokeError("http_error", f"provider returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SmokeError("network_error", f"provider request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise SmokeError("timeout", "provider request timed out") from exc

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    try:
        parsed = json.loads(response_body)
        returned_model = parsed["model"]
        response_text = parsed["choices"][0]["message"]["content"]
        usage = parsed.get("usage") or {}
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise SmokeError("response_invalid", "provider returned an invalid chat-completions response") from exc
    if returned_model != provider.model_id:
        raise SmokeError(
            "returned_model_mismatch",
            f"returned model does not match requested model for provider: {provider.provider}",
        )

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "provider": provider.provider,
        "api_base": provider.api_base,
        "api_key_source": f"env:{provider.api_key_env}",
        "requested_model": provider.model_id,
        "returned_model": returned_model,
        "http_status": http_status,
        "success": True,
        "request_id": request_id,
        "elapsed_ms": elapsed_ms,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "response_body_sha256": _sha256(response_body),
        "response_text_sha256": _sha256(str(response_text).encode("utf-8")),
        "mode": "live",
        "response_text_stored": False,
    }


def write_evidence_exclusive(path: Path, record: dict[str, object]) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    except FileExistsError as exc:
        raise SmokeError("evidence_exists", f"evidence file already exists: {path}") from exc

