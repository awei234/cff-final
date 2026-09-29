from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


VALID_EVENT_STATUSES = {"success", "failed", "denied", "not_called"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_event(event: dict[str, Any]) -> None:
    required = {"event_id", "scenario_id", "seed", "operation_id", "tool", "action", "target", "started_at", "finished_at", "status", "detail"}
    missing = required - event.keys()
    if missing:
        raise ValueError(f"event missing fields: {sorted(missing)}")
    if event["status"] not in VALID_EVENT_STATUSES:
        raise ValueError(f"invalid event status: {event['status']}")
