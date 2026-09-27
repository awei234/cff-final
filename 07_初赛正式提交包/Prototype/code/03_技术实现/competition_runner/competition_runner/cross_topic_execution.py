"""Fail-closed offline execution gate for the frozen cross-topic protocol."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .cross_topic import validate_cross_topic_protocol


class CrossTopicExecutionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CrossTopicExecutionError(
            "evidence_unreadable", f"unable to read JSON evidence: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise CrossTopicExecutionError(
            "evidence_invalid", f"JSON evidence must be an object: {path}"
        )
    return value


def _write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise CrossTopicExecutionError(
            "evidence_exists", f"refusing to overwrite dry-run evidence: {path}"
        ) from exc


def dry_run_cross_topic_protocol(
    *,
    protocol_path: Path,
    provider_config_path: Path,
    output_root: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Classify all frozen tasks without loading credentials or writing results."""
    if report_path.exists():
        raise CrossTopicExecutionError(
            "evidence_exists", f"refusing to overwrite dry-run evidence: {report_path}"
        )
    protocol = _read_json(protocol_path)
    try:
        provider_sha256 = sha256(provider_config_path.read_bytes()).hexdigest().upper()
    except OSError as exc:
        raise CrossTopicExecutionError(
            "provider_config_unreadable",
            f"unable to read provider configuration: {provider_config_path}",
        ) from exc
    if protocol.get("provider_config_sha256") != provider_sha256:
        raise CrossTopicExecutionError(
            "provider_config_drift",
            "provider configuration does not match the frozen protocol",
        )

    validation = validate_cross_topic_protocol(protocol, output_root=output_root)
    if not validation["valid"]:
        code = (
            "formal_output_exists"
            if "cross_topic_output_exists" in validation["errors"]
            else "protocol_invalid"
        )
        raise CrossTopicExecutionError(
            code,
            f"cross-topic protocol validation failed: {validation['errors']}",
        )

    classified: list[dict[str, Any]] = []
    for task in protocol["tasks"]:
        dry_run_status = (
            "blocked_budget"
            if task["provider"] == "deepseek" or task["status"] == "blocked_budget"
            else "eligible_not_executed"
        )
        classified.append(
            {
                "task_id": task["task_id"],
                "topic_id": task["topic_id"],
                "topic": task["topic"],
                "provider": task["provider"],
                "model_id": task["model_id"],
                "seed": task["seed"],
                "output_relpath": task["output_relpath"],
                "input_sha256": task["input_sha256"],
                "dry_run_status": dry_run_status,
            }
        )
    statuses = Counter(task["dry_run_status"] for task in classified)
    report: dict[str, Any] = {
        "schema_version": 1,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol["protocol_sha256"],
        "protocol_file_sha256": sha256(protocol_path.read_bytes()).hexdigest().upper(),
        "provider_config_sha256": provider_sha256,
        "source_commit": protocol["source_commit"],
        "mode": "offline_dry_run",
        "valid": True,
        "model_api_calls": 0,
        "api_key_reads": 0,
        "results_written": 0,
        "live_execution_enabled": False,
        "required_artifact_count": len(protocol["required_artifacts"]),
        "task_counts": {
            "total": len(classified),
            "eligible_not_executed": statuses["eligible_not_executed"],
            "blocked_budget": statuses["blocked_budget"],
        },
        "output_root": str(output_root),
        "tasks": classified,
    }
    _write_json_exclusive(report_path, report)
    return report


__all__ = ["CrossTopicExecutionError", "dry_run_cross_topic_protocol"]
