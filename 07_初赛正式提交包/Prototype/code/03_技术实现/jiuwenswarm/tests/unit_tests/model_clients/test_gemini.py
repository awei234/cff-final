import asyncio
from types import SimpleNamespace

from jiuwenswarm.model_clients.gemini import (
    build_gemini_request,
    parse_gemini_response,
)
from jiuwenswarm.common.model_factory import create_configured_model


def test_gemini_request_maps_system_messages_tools_and_limits():
    request = build_gemini_request(
        messages=[
            {"role": "system", "content": "Be concise"},
            {"role": "user", "content": "Hi"},
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "description": "Find",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        model="gemini-test",
        temperature=0.2,
        top_p=0.8,
        max_tokens=32,
        stop=["END"],
    )
    assert request.model == "gemini-test"
    assert request.config.system_instruction == "Be concise"
    assert request.contents[0].role == "user"
    assert request.contents[0].parts[0].text == "Hi"
    assert request.config.max_output_tokens == 32
    assert request.config.stop_sequences == ["END"]
    assert request.config.tools[0].function_declarations[0].name == "lookup"


def test_gemini_request_maps_assistant_tool_call_and_tool_result():
    request = build_gemini_request(
        messages=[
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "lookup", "arguments": '{"q":"x"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call-1", "name": "lookup", "content": '{"value":1}'},
        ],
        tools=None,
        model="gemini-test",
    )
    assert request.contents[0].role == "model"
    assert request.contents[0].parts[0].function_call.name == "lookup"
    assert request.contents[1].parts[0].function_response.name == "lookup"


def test_gemini_response_parses_text_function_calls_and_usage():
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(text="hello", function_call=None),
                        SimpleNamespace(
                            text=None,
                            function_call=SimpleNamespace(name="lookup", args={"q": "x"}, id="call-1"),
                        ),
                    ]
                ),
                finish_reason="STOP",
            )
        ],
        usage_metadata=SimpleNamespace(
            prompt_token_count=5,
            candidates_token_count=3,
            total_token_count=8,
            cached_content_token_count=2,
        ),
    )
    message = parse_gemini_response(response, "gemini-test")
    assert message.content == "hello"
    assert message.tool_calls[0].name == "lookup"
    assert message.tool_calls[0].arguments == '{"q": "x"}'
    assert message.usage_metadata.total_tokens == 8
    assert message.usage_metadata.cache_tokens == 2
    assert message.finish_reason == "tool_calls"


def test_gemini_empty_response_is_safe():
    message = parse_gemini_response(SimpleNamespace(candidates=[], usage_metadata=None), "gemini-test")
    assert message.content == ""
    assert message.tool_calls is None


def test_gemini_stream_uses_native_async_path_and_closes_client():
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[SimpleNamespace(text="hello", function_call=None)]),
                finish_reason="STOP",
            )
        ],
        usage_metadata=None,
    )

    class FakeModels:
        async def generate_content_stream(self, **kwargs):
            assert kwargs["model"] == "gemini-test"

            async def responses():
                yield response

            return responses()

    class FakeAsyncClient:
        def __init__(self):
            self.models = FakeModels()
            self.closed = False

        async def aclose(self):
            self.closed = True

    fake_async = FakeAsyncClient()
    fake_client = SimpleNamespace(aio=fake_async)
    model = create_configured_model(
        {
            "client_provider": "Gemini",
            "api_base": "https://generativelanguage.googleapis.com",
            "api_key": "test-key",
            "model_name": "gemini-test",
            "verify_ssl": False,
        },
        {},
    )
    model._client._client = lambda timeout=None: fake_client

    async def collect():
        return [chunk async for chunk in model._client.stream("Hi")]

    chunks = asyncio.run(collect())
    assert [chunk.content for chunk in chunks] == ["hello"]
    assert fake_async.closed is True
