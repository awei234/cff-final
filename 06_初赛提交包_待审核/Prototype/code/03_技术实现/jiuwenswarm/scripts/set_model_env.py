#!/usr/bin/env python3
"""Atomically update the model routing tuple in a JiuwenSwarm .env file."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile


FIELD_VALUES = {
    "MODEL_PROVIDER": "provider",
    "API_BASE": "api_base",
    "API_KEY": "api_key",
    "MODEL_NAME": "model",
}


def _quoted(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def update_model_env(
    path: Path,
    *,
    provider: str,
    api_base: str,
    api_key: str,
    model: str,
) -> None:
    values = {
        "MODEL_PROVIDER": provider.strip(),
        "API_BASE": api_base.strip().rstrip("/"),
        "API_KEY": api_key.strip(),
        "MODEL_NAME": model.strip(),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ValueError(f"Missing required model fields: {', '.join(missing)}")

    original = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = original.splitlines()
    updated: set[str] = set()
    output: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
        if key in values and not stripped.startswith("#"):
            output.append(f"{key}={_quoted(values[key])}")
            updated.add(key)
        else:
            output.append(line)
    for key in FIELD_VALUES:
        if key not in updated:
            output.append(f"{key}={_quoted(values[key])}")

    path.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = path.stat().st_mode if path.exists() else None
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(output) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if existing_mode is not None:
            os.chmod(temp_name, existing_mode)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("env_file", type=Path)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--api-base", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    update_model_env(
        args.env_file,
        provider=args.provider,
        api_base=args.api_base,
        api_key=args.api_key,
        model=args.model,
    )
    print(f"Updated model provider={args.provider} model={args.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
