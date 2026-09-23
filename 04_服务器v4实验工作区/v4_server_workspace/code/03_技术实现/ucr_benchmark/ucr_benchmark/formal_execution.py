from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from .experiment import ModelAdapter, run_one
from .formal_matrix import validate_formal_matrix


class ProviderCommandModelAdapter:
    def __init__(
        self,
        *,
        command: Sequence[str],
        prepared: dict[str, Any],
        environ: Mapping[str, str],
        timeout_seconds: float = 300,
    ) -> None:
        if not command:
            raise ValueError("model command must not be empty")
        provider = prepared["provider"]
        key = environ.get(provider["api_key_env"], "").strip()
        if not key:
            raise ValueError("api_key_missing")
        self.command = list(command)
        self.model_id = str(provider["model_id"])
        self.api_base = str(provider["api_base"])
        self.api_key = key
        self.sensitive_env_names = tuple(prepared["sensitive_env_names"])
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str, config: dict[str, Any]) -> str:
        generation = config["generation"]
        env = os.environ.copy()
        for name in self.sensitive_env_names:
            env.pop(name, None)
        env.update(
            {
                "OPENAI_COMPAT_API_BASE": self.api_base,
                "OPENAI_COMPAT_API_KEY": self.api_key,
                "OPENAI_COMPAT_MODEL": self.model_id,
                "UCR_ARM": str(config["arm"]),
                "UCR_SEED": str(config["seed"]),
                "UCR_TEMPERATURE": str(generation["temperature"]),
                "UCR_MAX_TOKENS": str(generation["max_tokens"]),
            }
        )
        completed = subprocess.run(
            self.command,
            input=prompt,
            text=True,
            capture_output=True,
            shell=False,
            timeout=self.timeout_seconds,
            env=env,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"model command failed with exit {completed.returncode}: "
                f"{completed.stderr[:500]}"
            )
        return completed.stdout.strip()


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest().upper()


def _write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def dry_run_formal_execution(
    *,
    manifest_path: Path,
    provider_config_path: Path,
    scenario_path: Path,
    output_root: Path,
    report_path: Path,
) -> dict[str, Any]:
    matrix = json.loads(manifest_path.read_text(encoding="utf-8"))
    if matrix.get("provider_config_sha256") != _sha256_file(provider_config_path):
        raise ValueError("provider_config_hash_mismatch")
    if matrix.get("scenario_sha256") != _sha256_file(scenario_path):
        raise ValueError("scenario_hash_mismatch")
    validation = validate_formal_matrix(matrix, output_root=output_root)
    if not validation["valid"]:
        raise ValueError(f"formal_matrix_invalid: {validation['errors']}")

    actions = [
        "blocked_budget"
        if task["status"] == "blocked_budget"
        else "eligible_not_executed"
        for task in matrix["tasks"]
    ]
    action_counts = Counter(actions)
    per_provider: dict[str, Counter[str]] = defaultdict(Counter)
    for task, action in zip(matrix["tasks"], actions, strict=True):
        per_provider[task["provider"]][action] += 1
    report = {
        "mode": "offline_dry_run",
        "model_api_calls": 0,
        "results_written": 0,
        "experiment_id": matrix["experiment_id"],
        "task_counts": {
            "selected": len(matrix["tasks"]),
            "eligible_not_executed": action_counts["eligible_not_executed"],
            "blocked_budget": action_counts["blocked_budget"],
        },
        "provider_counts": {
            provider: dict(counts) for provider, counts in per_provider.items()
        },
        "output_root": str(output_root),
    }
    _write_json_exclusive(report_path, report)
    return report


def prepare_formal_task(
    *,
    manifest_path: Path,
    provider_config_path: Path,
    scenario_path: Path,
    output_root: Path,
    task_id: str,
    environ: Mapping[str, str],
) -> dict[str, Any]:
    matrix = json.loads(manifest_path.read_text(encoding="utf-8"))
    if matrix.get("provider_config_sha256") != _sha256_file(provider_config_path):
        raise ValueError("provider_config_hash_mismatch")
    if matrix.get("scenario_sha256") != _sha256_file(scenario_path):
        raise ValueError("scenario_hash_mismatch")
    task = next(
        (item for item in matrix.get("tasks", []) if item.get("task_id") == task_id),
        None,
    )
    if task is None:
        raise ValueError("formal_task_unknown")
    validation = validate_formal_matrix(
        matrix,
        output_root=output_root,
        selected_output_relpaths={str(task.get("output_relpath", ""))},
    )
    if not validation["valid"]:
        raise ValueError(f"formal_matrix_invalid: {validation['errors']}")
    if task.get("status") == "blocked_budget":
        raise ValueError("task_blocked_budget")
    providers = json.loads(provider_config_path.read_text(encoding="utf-8"))
    provider = providers[task["provider"]]
    if (
        provider["model_id"] != task["model_id"]
        or provider["api_key_env"] != task["api_key_env"]
    ):
        raise ValueError("provider_task_mismatch")
    provider_report = {
        "api_base": provider["api_base"],
        "model_id": provider["model_id"],
        "api_key_env": provider["api_key_env"],
        "api_key_present": bool(environ.get(provider["api_key_env"], "").strip()),
    }
    output_path = output_root / task["output_relpath"]
    if output_path.exists():
        raise ValueError("formal_output_exists")
    return {
        "task": task,
        "provider": provider_report,
        "output_path": output_path,
        "sensitive_env_names": sorted(
            entry["api_key_env"] for entry in providers.values()
        ),
    }


def execute_prepared_formal_task(
    *,
    prepared: dict[str, Any],
    adapter: ModelAdapter,
    scenario_path: Path,
) -> Path:
    task = prepared["task"]
    if adapter.model_id != task["model_id"]:
        raise ValueError("adapter_model_mismatch")
    output_path = prepared["output_path"]
    provider_root = output_path.parents[1]
    return run_one(
        task["arm"],
        task["seed"],
        adapter,
        provider_root,
        manifest_path=scenario_path,
        formal_task=task,
    )


__all__ = [
    "ProviderCommandModelAdapter",
    "dry_run_formal_execution",
    "execute_prepared_formal_task",
    "prepare_formal_task",
]
