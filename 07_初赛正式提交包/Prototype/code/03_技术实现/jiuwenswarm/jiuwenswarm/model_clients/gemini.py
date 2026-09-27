"""Google Gemini adapter for OpenJiuwen's model-client interface."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, List, Optional, Union

from google import genai
from google.genai import types
from openjiuwen.core.foundation.llm.model_clients.base_model_client import BaseModelClient
from openjiuwen.core.foundation.llm.output_parsers.output_parser import BaseOutputParser
from openjiuwen.core.foundation.llm.schema import (
    AudioGenerationResponse,
    ImageGenerationResponse,
    VideoGenerationResponse,
)
from openjiuwen.core.foundation.llm.schema.config import ModelClientConfig, ModelRequestConfig
from openjiuwen.core.foundation.llm.schema.message import (
    AssistantMessage,
    BaseMessage,
    UsageMetadata,
    UserMessage,
)
from openjiuwen.core.foundation.llm.schema.message_chunk import AssistantMessageChunk
from openjiuwen.core.foundation.llm.schema.tool_call import ToolCall
from openjiuwen.core.foundation.tool import ToolInfo

from jiuwenswarm.common.model_providers import classify_model_error


@dataclass(frozen=True)
class GeminiRequest:
    model: str
    contents: list[types.Content]
    config: types.GenerateContentConfig


def _message_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                value = item.get("text") or item.get("content")
                if value:
                    texts.append(str(value))
        return "\n".join(texts)
    return str(content)


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"result": parsed}
        except json.JSONDecodeError:
            return {"result": value}
    return {"result": value}


def _openai_tools(tools: Union[List[ToolInfo], List[dict], None]) -> list[dict]:
    return BaseModelClient._convert_tools_to_dict(tools) or []


def _gemini_tools(tools: Union[List[ToolInfo], List[dict], None]) -> list[types.Tool] | None:
    declarations: list[types.FunctionDeclaration] = []
    for tool in _openai_tools(tools):
        function = tool.get("function", tool)
        if not function.get("name"):
            continue
        declarations.append(
            types.FunctionDeclaration(
                name=str(function["name"]),
                description=str(function.get("description") or ""),
                parameters_json_schema=function.get("parameters") or {"type": "object"},
            )
        )
    return [types.Tool(function_declarations=declarations)] if declarations else None


def _gemini_contents(messages: Union[str, List[BaseMessage], List[dict]]) -> tuple[str | None, list[types.Content]]:
    openai_messages = BaseModelClient._convert_messages_to_dict(messages)
    system_parts: list[str] = []
    contents: list[types.Content] = []
    tool_names: dict[str, str] = {}
    for message in openai_messages:
        role = str(message.get("role") or "user").lower()
        text = _message_text(message.get("content"))
        if role in {"system", "developer"}:
            if text:
                system_parts.append(text)
            continue

        parts: list[types.Part] = []
        if text:
            parts.append(types.Part(text=text))
        if role == "assistant":
            for call in message.get("tool_calls") or []:
                function = call.get("function") or {}
                call_id = str(call.get("id") or "")
                name = str(function.get("name") or "")
                if call_id and name:
                    tool_names[call_id] = name
                parts.append(
                    types.Part(
                        function_call=types.FunctionCall(
                            id=call_id or None,
                            name=name,
                            args=_json_object(function.get("arguments") or {}),
                        )
                    )
                )
            gemini_role = "model"
        elif role == "tool":
            call_id = str(message.get("tool_call_id") or "")
            name = str(message.get("name") or tool_names.get(call_id) or "tool")
            parts = [
                types.Part(
                    function_response=types.FunctionResponse(
                        id=call_id or None,
                        name=name,
                        response=_json_object(message.get("content")),
                    )
                )
            ]
            gemini_role = "user"
        else:
            gemini_role = "user"
        if parts:
            contents.append(types.Content(role=gemini_role, parts=parts))
    return "\n\n".join(system_parts) or None, contents


def build_gemini_request(
    *,
    messages: Union[str, List[BaseMessage], List[dict]],
    tools: Union[List[ToolInfo], List[dict], None],
    model: str,
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
    stop: str | list[str] | None = None,
) -> GeminiRequest:
    system_instruction, contents = _gemini_contents(messages)
    stops = [stop] if isinstance(stop, str) else stop
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_tokens,
        stop_sequences=stops,
        tools=_gemini_tools(tools),
    )
    return GeminiRequest(model=model, contents=contents, config=config)


def _usage_metadata(response: Any, model_name: str) -> UsageMetadata | None:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
    total_tokens = int(getattr(usage, "total_token_count", 0) or 0) or input_tokens + output_tokens
    cache_tokens = int(getattr(usage, "cached_content_token_count", 0) or 0)
    return UsageMetadata(
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cache_tokens=cache_tokens,
    )


def parse_gemini_response(response: Any, model_name: str) -> AssistantMessage:
    candidates = list(getattr(response, "candidates", None) or [])
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    finish_reason = "stop"
    if candidates:
        candidate = candidates[0]
        content = getattr(candidate, "content", None)
        for index, part in enumerate(getattr(content, "parts", None) or []):
            text = getattr(part, "text", None)
            if text:
                text_parts.append(str(text))
            function_call = getattr(part, "function_call", None)
            if function_call:
                tool_calls.append(
                    ToolCall(
                        id=str(getattr(function_call, "id", None) or f"gemini-call-{index}"),
                        type="function",
                        name=str(getattr(function_call, "name", "") or ""),
                        arguments=json.dumps(
                            dict(getattr(function_call, "args", None) or {}),
                            ensure_ascii=False,
                        ),
                        index=index,
                    )
                )
        reason = str(getattr(candidate, "finish_reason", "") or "").lower()
        finish_reason = "stop" if reason in {"", "stop", "max_tokens"} else reason
    if tool_calls:
        finish_reason = "tool_calls"
    return AssistantMessage(
        content="".join(text_parts),
        tool_calls=tool_calls or None,
        usage_metadata=_usage_metadata(response, model_name),
        finish_reason=finish_reason,
    )


class GeminiModelClient(BaseModelClient):
    __client_name__ = "Gemini"

    def _get_client_name(self) -> str:
        return "Gemini client"

    def _validate_config(self) -> None:
        if not str(self.model_client_config.api_key or "").strip():
            raise ValueError("Gemini API key is required.")
        if not str(self.model_client_config.api_base or "").strip():
            raise ValueError("Gemini Base URL is required.")

    def _client(self, timeout: float | None = None) -> genai.Client:
        timeout_ms = int(1000 * (timeout or self.model_client_config.timeout))
        return genai.Client(
            api_key=self.model_client_config.api_key,
            http_options=types.HttpOptions(
                base_url=self.model_client_config.api_base.rstrip("/"),
                timeout=timeout_ms,
                headers=self.model_client_config.custom_headers,
            ),
        )

    def _request(self, messages, tools, temperature, top_p, model, max_tokens, stop) -> GeminiRequest:
        return build_gemini_request(
            messages=messages,
            tools=tools,
            model=model or self.model_config.model_name,
            temperature=temperature if temperature is not None else self.model_config.temperature,
            top_p=top_p if top_p is not None else self.model_config.top_p,
            max_tokens=max_tokens if max_tokens is not None else self.model_config.max_tokens,
            stop=stop if stop is not None else self.model_config.stop,
        )

    async def invoke(
        self,
        messages,
        *,
        tools=None,
        temperature=None,
        top_p=None,
        model=None,
        max_tokens=None,
        stop=None,
        output_parser: Optional[BaseOutputParser] = None,
        timeout=None,
        **kwargs,
    ) -> AssistantMessage:
        del kwargs
        request = self._request(messages, tools, temperature, top_p, model, max_tokens, stop)
        client = self._client(timeout)
        try:
            response = await client.aio.models.generate_content(
                model=request.model, contents=request.contents, config=request.config
            )
            result = parse_gemini_response(response, request.model)
            if output_parser and result.content:
                result.parser_content = await output_parser.parse(result.content)
            return result
        except Exception as exc:
            classified = classify_model_error(exc)
            raise RuntimeError(f"{classified.code}: {classified.message}") from exc
        finally:
            await client.aio.aclose()

    async def stream(
        self,
        messages,
        *,
        tools=None,
        temperature=None,
        top_p=None,
        model=None,
        max_tokens=None,
        stop=None,
        output_parser=None,
        timeout=None,
        **kwargs,
    ) -> AsyncIterator[AssistantMessageChunk]:
        del output_parser, kwargs
        request = self._request(messages, tools, temperature, top_p, model, max_tokens, stop)
        client = self._client(timeout)
        try:
            async for response in await client.aio.models.generate_content_stream(
                model=request.model, contents=request.contents, config=request.config
            ):
                parsed = parse_gemini_response(response, request.model)
                yield AssistantMessageChunk(
                    content=parsed.content,
                    tool_calls=parsed.tool_calls,
                    usage_metadata=parsed.usage_metadata,
                    finish_reason=parsed.finish_reason,
                )
        except Exception as exc:
            classified = classify_model_error(exc)
            raise RuntimeError(f"{classified.code}: {classified.message}") from exc
        finally:
            await client.aio.aclose()

    async def generate_image(self, messages: List[UserMessage], **kwargs) -> ImageGenerationResponse:
        raise NotImplementedError("Image generation is not supported by GeminiModelClient.")

    async def generate_speech(self, messages: List[UserMessage], **kwargs) -> AudioGenerationResponse:
        raise NotImplementedError("Speech generation is not supported by GeminiModelClient.")

    async def generate_video(self, messages: List[UserMessage], **kwargs) -> VideoGenerationResponse:
        raise NotImplementedError("Video generation is not supported by GeminiModelClient.")


__all__ = [
    "GeminiModelClient",
    "GeminiRequest",
    "build_gemini_request",
    "parse_gemini_response",
]
