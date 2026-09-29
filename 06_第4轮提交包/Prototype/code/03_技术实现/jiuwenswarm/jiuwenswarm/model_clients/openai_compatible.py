"""Neutral OpenAI-compatible model client.

Unlike ``DeepSeekModelClient``, this client does not add DeepSeek-only message
fields, so it is safe for GLM, private gateways, and other compatible APIs.
"""

from openjiuwen.core.foundation.llm.model_clients.openai_model_client import (
    OpenAIModelClient,
)


class OpenAICompatibleModelClient(OpenAIModelClient):
    __client_name__ = "OpenAICompatible"

    def _get_client_name(self) -> str:
        return "OpenAI-compatible client"


__all__ = ["OpenAICompatibleModelClient"]
