from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from collections import Counter


ARMS = ("no-rail", "prompt-only", "full-rail")
SEEDS = tuple(range(42, 52))
BLOCKED_PROVIDERS = frozenset({"deepseek"})
PARAMETERS = {"temperature": 0.2, "max_tokens": 4096}


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest().upper()


def build_formal_matrix(
    *,
    provider_config_path: Path,
    scenario_path: Path,
    source_commit: str,
) -> dict[str, Any]:
    providers = json.loads(provider_config_path.read_text(encoding="utf-8"))
    scenario_sha256 = sha256(scenario_path.read_bytes()).hexdigest().upper()
    tasks: list[dict[str, Any]] = []
    for provider, provider_config in providers.items():
        for arm in ARMS:
            for seed in SEEDS:
                task = {
                    "task_id": f"{provider}-{arm}-seed{seed}",
                    "provider": provider,
                    "model_id": provider_config["model_id"],
                    "api_key_env": provider_config["api_key_env"],
                    "arm": arm,
                    "seed": seed,
                    "temperature": PARAMETERS["temperature"],
                    "max_tokens": PARAMETERS["max_tokens"],
                    "scenario_sha256": scenario_sha256,
                    "source_commit": source_commit,
                    "output_relpath": f"{provider}/{arm}/seed{seed}",
                    "status": (
                        "blocked_budget"
                        if provider in BLOCKED_PROVIDERS
                        else "pending"
                    ),
                }
                task["input_sha256"] = _canonical_sha256(task)
                tasks.append(task)
    return {
        "schema_version": 1,
        "experiment_id": "ucr-formal-s3-v1",
        "source_commit": source_commit,
        "provider_config_sha256": sha256(
            provider_config_path.read_bytes()
        ).hexdigest().upper(),
        "scenario_sha256": scenario_sha256,
        "providers": list(providers),
        "arms": list(ARMS),
        "seeds": list(SEEDS),
        "parameters": dict(PARAMETERS),
        "blocked_providers": sorted(BLOCKED_PROVIDERS),
        "tasks": tasks,
        "tasks_sha256": _canonical_sha256(tasks),
    }


def validate_formal_matrix(
    matrix: dict[str, Any],
    *,
    output_root: Path,
    selected_output_relpaths: set[str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    existing_outputs: list[str] = []
    tasks = matrix.get("tasks")
    if not isinstance(tasks, list):
        return {
            "valid": False,
            "errors": ["tasks_missing"],
            "existing_outputs": [],
        }
    for task in tasks:
        if not isinstance(task, dict):
            errors.append("task_invalid")
            continue
        if (
            task.get("provider") in BLOCKED_PROVIDERS
            and task.get("status") != "blocked_budget"
        ):
            errors.append("blocked_provider_executable")
        output_relpath = task.get("output_relpath")
        selected = (
            selected_output_relpaths is None
            or output_relpath in selected_output_relpaths
        )
        if (
            selected
            and isinstance(output_relpath, str)
            and (output_root / output_relpath).exists()
        ):
            existing_outputs.append(output_relpath)
        frozen_input = {key: value for key, value in task.items() if key != "input_sha256"}
        if task.get("input_sha256") != _canonical_sha256(frozen_input):
            errors.append("task_input_hash_mismatch")
    if existing_outputs:
        errors.append("formal_output_exists")
    expected_task_ids = {
        f"{provider}-{arm}-seed{seed}"
        for provider in ("glm", "qwen", "deepseek")
        for arm in ARMS
        for seed in SEEDS
    }
    actual_task_ids = {
        task.get("task_id")
        for task in tasks
        if isinstance(task, dict)
    }
    if len(tasks) != 90 or actual_task_ids != expected_task_ids:
        errors.append("formal_matrix_incomplete")
    if matrix.get("tasks_sha256") != _canonical_sha256(tasks):
        errors.append("tasks_hash_mismatch")
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "existing_outputs": sorted(existing_outputs),
    }


def _write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def freeze_formal_matrix(
    *,
    provider_config_path: Path,
    scenario_path: Path,
    source_commit: str,
    output_root: Path,
    manifest_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    for path in (manifest_path, report_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite frozen evidence: {path}")
    matrix = build_formal_matrix(
        provider_config_path=provider_config_path,
        scenario_path=scenario_path,
        source_commit=source_commit,
    )
    report = validate_formal_matrix(matrix, output_root=output_root)
    if not report["valid"]:
        raise ValueError(f"formal matrix preflight failed: {report['errors']}")
    statuses = Counter(task["status"] for task in matrix["tasks"])
    report.update(
        {
            "mode": "offline_preflight",
            "model_api_calls": 0,
            "experiment_id": matrix["experiment_id"],
            "matrix_sha256": _canonical_sha256(matrix),
            "task_counts": {
                "total": len(matrix["tasks"]),
                "pending": statuses["pending"],
                "blocked_budget": statuses["blocked_budget"],
            },
            "output_root": str(output_root),
        }
    )
    _write_json_exclusive(manifest_path, matrix)
    _write_json_exclusive(report_path, report)
    return report


__all__ = [
    "build_formal_matrix",
    "freeze_formal_matrix",
    "validate_formal_matrix",
]
