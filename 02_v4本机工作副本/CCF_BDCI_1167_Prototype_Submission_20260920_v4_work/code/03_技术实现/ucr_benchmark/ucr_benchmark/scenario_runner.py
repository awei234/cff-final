from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schema import read_jsonl, sha256_bytes, validate_event, write_jsonl


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bounded(error: BaseException | str, limit: int = 500) -> str:
    if isinstance(error, BaseException):
        value = f"{type(error).__name__}: {error}"
    else:
        value = error
    return value[:limit]


def _base_event(item: dict[str, Any], seed: int, index: int) -> dict[str, Any]:
    operation_id = str(item["operation_id"])
    return {
        "event_id": f"seed{seed}-{index:02d}-{operation_id}",
        "scenario_id": str(item.get("scenario_id", "ucr-core")),
        "seed": seed,
        "operation_id": operation_id,
        "tool": str(item.get("tool", item["kind"])),
        "action": str(item.get("action", "execute")),
        "target": str(item.get("target", operation_id)),
        "started_at": _now(),
        "finished_at": None,
        "status": "failed",
        "exit_code": None,
        "stdout_sha256": None,
        "stderr_sha256": None,
        "artifact_sha256": None,
        "detail": "",
    }


def _run_one(item: dict[str, Any], seed: int, index: int, run_dir: Path) -> dict[str, Any]:
    event = _base_event(item, seed, index)
    kind = item["kind"]
    try:
        if kind == "command":
            argv = [part.replace("{python}", sys.executable) for part in item["argv"]]
            completed = subprocess.run(argv, cwd=run_dir, capture_output=True, timeout=float(item.get("timeout_seconds", 10)), shell=False)
            event.update(
                action=str(item.get("action", "execute")),
                target=str(item.get("target", " ".join(argv[1:]))),
                exit_code=completed.returncode,
                stdout_sha256=sha256_bytes(completed.stdout),
                stderr_sha256=sha256_bytes(completed.stderr),
                status="success" if completed.returncode == 0 else "failed",
                detail=_bounded(completed.stdout.decode("utf-8", errors="replace") if completed.returncode == 0 else completed.stderr.decode("utf-8", errors="replace")),
            )
        elif kind in {"read_file", "query_fixture"}:
            target = run_dir / item["target"]
            data = target.read_bytes()
            event.update(
                tool="filesystem" if kind == "read_file" else "local-query",
                action="inspect" if kind == "read_file" else "query",
                target=str(item["target"]),
                status="success",
                artifact_sha256=sha256_bytes(data),
                detail=_bounded(data.decode("utf-8", errors="replace")),
            )
        elif kind == "denied":
            event.update(action=str(item.get("action", "execute")), status="denied", detail=_bounded(str(item.get("detail", "operation denied"))))
        elif kind == "not_called":
            event.update(action=str(item.get("action", "execute")), status="not_called", detail=_bounded(str(item.get("detail", "tool was not called"))))
        else:
            raise ValueError(f"unsupported scenario kind: {kind}")
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        event.update(status="failed", detail=_bounded(exc))
    event["finished_at"] = _now()
    validate_event(event)
    return event


def run_scenarios(manifest: dict[str, Any], seed: int, run_dir: Path) -> list[dict[str, Any]]:
    run_dir.mkdir(parents=True, exist_ok=True)
    events = [_run_one(item, seed, index, run_dir) for index, item in enumerate(manifest["scenarios"], start=1)]
    write_jsonl(run_dir / "tool_trace.jsonl", events)
    return events


def read_trace(path: Path) -> list[dict[str, Any]]:
    events = read_jsonl(path)
    for event in events:
        validate_event(event)
    return events
