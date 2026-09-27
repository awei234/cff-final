import pytest

from jiuwenswarm.common.model_providers import (
    ModelConfigurationError,
    get_provider_spec,
    list_model_providers,
    normalize_model_provider,
    validate_model_connection_config,
)


def test_catalog_includes_native_and_extension_providers():
    assert {
        "OpenAI",
        "OpenAICompatible",
        "Anthropic",
        "Gemini",
        "DashScope",
        "DeepSeek",
    } <= set(list_model_providers())


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("openai-compatible", "OpenAICompatible"),
        ("openai_compatible", "OpenAICompatible"),
        ("claude", "Anthropic"),
        ("google", "Gemini"),
        ("deepseek", "DeepSeek"),
    ],
)
def test_provider_aliases_normalize_without_model_name_guessing(value, expected):
    assert normalize_model_provider(value) == expected


def test_provider_defaults_are_transport_specific():
    assert get_provider_spec("OpenAI").default_api_base == "https://api.openai.com/v1"
    assert get_provider_spec("Anthropic").transport == "anthropic"
    assert get_provider_spec("Gemini").transport == "gemini"
    assert get_provider_spec("OpenAICompatible").transport == "openai_compatible"


@pytest.mark.parametrize(
    "value",
    ["", "not-a-url", "ftp://models.test", "https://example.com/v1"],
)
def test_validate_rejects_invalid_or_placeholder_base_url(value):
    with pytest.raises(ModelConfigurationError, match="Base URL"):
        validate_model_connection_config("OpenAI", value, "key", "gpt-test")


def test_validate_reports_missing_provider_key_and_model_separately():
    with pytest.raises(ModelConfigurationError, match="API key"):
        validate_model_connection_config(
            "Anthropic", "https://api.anthropic.com", "", "claude-test"
        )
    with pytest.raises(ModelConfigurationError, match="model name"):
        validate_model_connection_config(
            "Gemini", "https://generativelanguage.googleapis.com", "key", ""
        )


def test_validate_reports_unknown_provider():
    with pytest.raises(ModelConfigurationError, match="Unsupported model provider"):
        validate_model_connection_config(
            "UnknownVendor", "https://models.test/v1", "key", "model-test"
        )


def test_openai_account_does_not_require_user_api_key():
    validated = validate_model_connection_config(
        "OpenAIAccount",
        "https://chatgpt.com/backend-api/codex",
        "",
        "gpt-account",
    )
    assert validated.provider == "OpenAIAccount"


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ("401 invalid api key", "AUTH_ERROR"),
        ("model_not_found: unknown model", "MODEL_NOT_FOUND"),
        ("429 rate limit exceeded", "RATE_LIMITED"),
        ("certificate verify failed", "CONNECTION_ERROR"),
        ("unsupported client_provider", "PROVIDER_ERROR"),
        ("upstream exploded", "LLM_ERROR"),
    ],
)
def test_model_errors_are_classified_without_credentials(message, code):
    from jiuwenswarm.common.model_providers import classify_model_error

    classified = classify_model_error(RuntimeError(message))
    assert classified.code == code
    assert "sk-secret" not in classified.message
