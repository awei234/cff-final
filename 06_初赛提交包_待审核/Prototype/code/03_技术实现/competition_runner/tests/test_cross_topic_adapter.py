from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parents[1]
ADAPTER = BASE / "adapters" / "cross_topic_openai_compatible.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("cross_topic_openai_compatible", ADAPTER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adapter_builds_one_seeded_json_chat_request(monkeypatch):
    """Dropping the frozen model, seed, or JSON response contract would make live output unauditable."""
    monkeypatch.setenv("OPENAI_COMPAT_MODEL", "glm-5.2")
    adapter = _load_adapter()

    payload = adapter.build_request_payload(
        {
            "task": {"seed": 42},
            "prompt": "Run the frozen cross-topic pipeline.",
        }
    )

    assert payload["model"] == "glm-5.2"
    assert payload["messages"][1] == {
        "role": "user",
        "content": "Run the frozen cross-topic pipeline.",
    }
    assert payload["temperature"] == 0.2
    assert payload["max_tokens"] == 8192
    assert payload["seed"] == 42
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["thinking"] == {"type": "disabled"}

    system = payload["messages"][0]["content"]
    assert "exactly one JSON object" in system
    assert "Markdown code fences" in system
    for field in (
        "results",
        "paper_tex",
        "resource",
        "research_materials",
        "plan",
        "execution_report",
        "tool_events",
        "rail_events",
        "human_interventions",
    ):
        assert f'"{field}"' in system
    assert "non-empty ASCII LaTeX string" in system
    assert "paper_pdf_base64" not in system


def test_adapter_does_not_send_glm_thinking_parameter_to_qwen(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPAT_MODEL", "qwen-plus")
    adapter = _load_adapter()
    payload = adapter.build_request_payload(
        {"task": {"seed": 42}, "prompt": "Run the frozen cross-topic pipeline."}
    )
    assert "thinking" not in payload


def test_adapter_extracts_non_empty_structured_content():
    adapter = _load_adapter()
    content = '{"results": {}, "paper_tex": "evidence"}'
    response = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": content, "reasoning_content": ""},
            }
        ]
    }
    assert adapter.extract_response_content(response) == content


def test_adapter_rejects_empty_content_instead_of_printing_a_blank_bundle():
    adapter = _load_adapter()
    response = {
        "choices": [
            {
                "finish_reason": "length",
                "message": {"content": "", "reasoning_content": "internal reasoning"},
            }
        ]
    }
    with pytest.raises(ValueError, match="empty content"):
        adapter.extract_response_content(response)
