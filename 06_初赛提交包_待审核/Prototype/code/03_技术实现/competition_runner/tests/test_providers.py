from __future__ import annotations

import json

import pytest

from competition_runner.providers import ProviderConfigError, resolve_provider


CONFIG = {
    "glm": {
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "model_id": "glm-5.2",
        "api_key_env": "ZHIPUAI_API_KEY",
    },
    "qwen": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_id": "qwen-plus",
        "api_key_env": "DASHSCOPE_API_KEY",
    },
    "deepseek": {
        "api_base": "https://api.deepseek.com",
        "model_id": "deepseek-v4-flash",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
}


def write_config(tmp_path):
    path = tmp_path / "providers.json"
    path.write_text(json.dumps(CONFIG), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("provider", "model_id", "api_key_env"),
    [
        ("glm", "glm-5.2", "ZHIPUAI_API_KEY"),
        ("qwen", "qwen-plus", "DASHSCOPE_API_KEY"),
        ("deepseek", "deepseek-v4-flash", "DEEPSEEK_API_KEY"),
    ],
)
def test_provider_tuple_is_explicit_and_redacted(tmp_path, provider, model_id, api_key_env):
    """A provider selection must expose identity and key source, never a secret value."""
    secret = "synthetic-secret-that-must-not-appear"
    resolved = resolve_provider(
        provider=provider,
        config_path=write_config(tmp_path),
        environ={api_key_env: secret},
    )
    report = resolved.as_report()
    assert report == {
        "provider": provider,
        "api_base": CONFIG[provider]["api_base"],
        "model_id": model_id,
        "api_key_source": f"env:{api_key_env}",
        "api_key_present": True,
    }
    assert secret not in json.dumps(report)


def test_missing_key_fails_before_a_live_request(tmp_path):
    """Missing credentials must be an explicit preflight failure."""
    resolved = resolve_provider(
        provider="glm",
        config_path=write_config(tmp_path),
        environ={},
    )
    with pytest.raises(ProviderConfigError) as exc:
        resolved.load_api_key({})
    assert exc.value.code == "api_key_missing"
    assert "ZHIPUAI_API_KEY" in str(exc.value)


def test_cli_model_override_is_recorded(tmp_path):
    """The actually requested model must replace, not hide behind, the config default."""
    resolved = resolve_provider(
        provider="qwen",
        config_path=write_config(tmp_path),
        model_id="qwen-explicit-model",
        environ={"DASHSCOPE_API_KEY": "synthetic"},
    )
    assert resolved.model_id == "qwen-explicit-model"


def test_unknown_provider_is_rejected(tmp_path):
    """A typo must not route to a fallback provider."""
    with pytest.raises(ProviderConfigError) as exc:
        resolve_provider(
            provider="qwne",
            config_path=write_config(tmp_path),
            environ={},
        )
    assert exc.value.code == "provider_unknown"

