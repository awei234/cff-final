from __future__ import annotations

import hashlib
import json

import pytest

from competition_runner.providers import ResolvedProvider
from competition_runner.smoke import SmokeError, run_live_smoke, write_evidence_exclusive


class FakeResponse:
    status = 200

    def __init__(self, body: bytes) -> None:
        self._body = body
        self.headers = {"x-request-id": "request-123"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self._body


def test_live_smoke_uses_explicit_tuple_and_returns_sanitized_evidence():
    """A live call must use the chosen model while excluding the key and response text from evidence."""
    secret = "synthetic-live-secret"
    response_payload = {
        "id": "response-123",
        "model": "glm-5.2",
        "choices": [{"message": {"content": "OK"}}],
        "usage": {"prompt_tokens": 9, "completion_tokens": 2, "total_tokens": 11},
    }
    response_body = json.dumps(response_payload).encode("utf-8")
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(response_body)

    provider = ResolvedProvider(
        provider="glm",
        api_base="https://open.bigmodel.cn/api/paas/v4",
        model_id="glm-5.2",
        api_key_env="ZHIPUAI_API_KEY",
        api_key_present=True,
    )
    report = run_live_smoke(provider, secret, opener=opener, timeout_seconds=30)

    assert captured == {
        "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "authorization": f"Bearer {secret}",
        "payload": {
            "model": "glm-5.2",
            "messages": [{"role": "user", "content": "Reply with OK only."}],
            "temperature": 0,
            "max_tokens": 2,
        },
        "timeout": 30,
    }
    assert report["success"] is True
    assert report["provider"] == "glm"
    assert report["requested_model"] == "glm-5.2"
    assert report["returned_model"] == "glm-5.2"
    assert report["total_tokens"] == 11
    assert report["response_body_sha256"] == hashlib.sha256(response_body).hexdigest().upper()
    serialized = json.dumps(report)
    assert secret not in serialized
    assert "OK" not in serialized


def test_model_mismatch_is_an_explicit_failure():
    """A provider returning another model must not be recorded as a successful verification."""
    body = json.dumps(
        {
            "model": "different-model",
            "choices": [{"message": {"content": "OK"}}],
            "usage": {},
        }
    ).encode("utf-8")

    provider = ResolvedProvider(
        provider="qwen",
        api_base="https://example.invalid/v1",
        model_id="qwen-plus",
        api_key_env="DASHSCOPE_API_KEY",
        api_key_present=True,
    )
    with pytest.raises(SmokeError) as exc:
        run_live_smoke(provider, "synthetic", opener=lambda request, timeout: FakeResponse(body))
    assert exc.value.code == "returned_model_mismatch"


def test_evidence_writer_refuses_to_overwrite(tmp_path):
    """A rerun must not silently replace an earlier live result."""
    target = tmp_path / "smoke.jsonl"
    target.write_text("historical\n", encoding="utf-8")
    with pytest.raises(SmokeError) as exc:
        write_evidence_exclusive(target, {"success": True})
    assert exc.value.code == "evidence_exists"
    assert target.read_text(encoding="utf-8") == "historical\n"

