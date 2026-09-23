#!/usr/bin/env python3
"""One-call OpenAI-compatible adapter for a cross-topic JSON bundle."""

from __future__ import annotations

import json
import os
import sys
import urllib.request


SYSTEM_PROMPT = """Return exactly one JSON object and no Markdown code fences.
All fields are required. Use this shape and these types:
{
  "results": {},
  "paper_tex": "non-empty ASCII LaTeX string",
  "resource": {},
  "research_materials": {},
  "plan": {},
  "execution_report": {},
  "tool_events": [{}],
  "rail_events": [{}],
  "human_interventions": [{}]
}
Each event array must contain at least one object. Preserve failures inside the
corresponding objects; do not omit fields, invent measurements, or fabricate
evidence. Do not return a PDF or Base64 data."""


def build_request_payload(request: dict[str, object]) -> dict[str, object]:
    task = request["task"]
    model = os.environ["OPENAI_COMPAT_MODEL"]
    payload: dict[str, object] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {"role": "user", "content": request["prompt"]},
        ],
        "temperature": 0.2,
        "max_tokens": 8192,
        "seed": int(task["seed"]),
        "response_format": {"type": "json_object"},
    }
    if model.lower().startswith("glm-"):
        payload["thinking"] = {"type": "disabled"}
    return payload


def extract_response_content(response_value: object) -> str:
    try:
        choice = response_value["choices"][0]
        message = choice["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("provider response is missing content") from exc
    if not isinstance(content, str) or not content.strip():
        reasoning = message.get("reasoning_content", "")
        reasoning_bytes = len(reasoning.encode("utf-8")) if isinstance(reasoning, str) else 0
        raise ValueError(
            "provider response has empty content "
            f"(finish_reason={choice.get('finish_reason')!r}, reasoning_content_bytes={reasoning_bytes})"
        )
    return content


def main() -> int:
    base = os.environ.get("OPENAI_COMPAT_API_BASE", "").rstrip("/")
    key = os.environ.get("OPENAI_COMPAT_API_KEY", "")
    model = os.environ.get("OPENAI_COMPAT_MODEL", "")
    if not base or not key or not model:
        print("provider environment is incomplete", file=sys.stderr)
        return 2
    request_value = json.load(sys.stdin)
    payload = build_request_payload(request_value)
    request = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        response_value = json.load(response)
    try:
        content = extract_response_content(response_value)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
