import pytest

from jiuwenswarm.common.model_factory import create_configured_model
from jiuwenswarm.common.model_providers import ModelConfigurationError


@pytest.mark.parametrize(
    ("provider", "expected_client"),
    [
        ("OpenAI", "OpenAIModelClient"),
        ("OpenAICompatible", "OpenAICompatibleModelClient"),
        ("Anthropic", "AnthropicModelClient"),
        ("Gemini", "GeminiModelClient"),
        ("DashScope", "DashScopeModelClient"),
        ("DeepSeek", "DeepSeekModelClient"),
    ],
)
def test_create_configured_model_routes_provider_exactly(provider, expected_client):
    model = create_configured_model(
        {
            "client_provider": provider,
            "api_base": "https://models.test/v1",
            "api_key": "test-key",
            "model_name": "model-test",
            "verify_ssl": False,
        },
        {"temperature": 0.2},
    )
    assert type(model._client).__name__ == expected_client


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ({"api_base": "https://models.test", "api_key": "key", "model_name": "x"}, "provider"),
        ({"client_provider": "OpenAI", "api_key": "key", "model_name": "x"}, "Base URL"),
        ({"client_provider": "OpenAI", "api_base": "https://models.test", "model_name": "x"}, "API key"),
        ({"client_provider": "OpenAI", "api_base": "https://models.test", "api_key": "key"}, "model name"),
    ],
)
def test_create_configured_model_reports_invalid_fields(entry, message):
    with pytest.raises(ModelConfigurationError, match=message):
        create_configured_model(entry, {})
