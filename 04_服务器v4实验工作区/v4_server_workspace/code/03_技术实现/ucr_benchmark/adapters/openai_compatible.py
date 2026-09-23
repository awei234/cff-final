#!/usr/bin/env python3
"""stdin/stdout adapter for an OpenAI-compatible chat-completions endpoint."""

from __future__ import annotations

import json
import os
import sys
import urllib.request


def build_request_payload(
    *,
    prompt: str,
    model: str,
    seed: int,
    temperature: float,
    max_tokens: int,
) -> dict[str, object]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "seed": seed,
    }


def main() -> int:
    base = os.environ.get("OPENAI_COMPAT_API_BASE", "").rstrip("/")
    key = os.environ.get("OPENAI_COMPAT_API_KEY", "")
    model = os.environ.get("OPENAI_COMPAT_MODEL", "")
    if not base or not key or not model:
        print("Set OPENAI_COMPAT_API_BASE, OPENAI_COMPAT_API_KEY, and OPENAI_COMPAT_MODEL", file=sys.stderr)
        return 2
    payload = build_request_payload(
        prompt=sys.stdin.read(),
        model=model,
        seed=int(os.environ.get("UCR_SEED", "42")),
        temperature=float(os.environ.get("UCR_TEMPERATURE", "0.2")),
        max_tokens=int(os.environ.get("UCR_MAX_TOKENS", "4096")),
    )
    request = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.load(response)
    print(data["choices"][0]["message"]["content"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
