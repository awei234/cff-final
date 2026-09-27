"""Freeze and preflight the budget-aware cross-topic generalization protocol."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


TOPICS = (
    {"topic_id": "context-engineering", "title": "Agent上下文工程"},
    {"topic_id": "memory-engine", "title": "Agent记忆引擎"},
    {"topic_id": "self-evolution", "title": "Agent自演进"},
)
PROVIDERS = ("glm", "qwen", "deepseek")
SEED = 42
PROMPT_TEMPLATE = (
    "Run the unified research pipeline for topic: {topic}. "
    "Do not reuse prior paper claims or results; preserve failures as evidence."
)
REQUIRED_ARTIFACTS = (
    "run_manifest.json",
    "prompt.txt",
    "tool_trace.jsonl",
    "results.json",
    "paper.tex",
    "paper.pdf",
    "resource.json",
    "verification_report.json",
    "provenance.json",
    "research_materials.json",
    "plan.json",
    "execution_report.json",
    "rail_events.jsonl",
    "human_interventions.jsonl",
)


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest().upper()


def _without_hash(value: dict[str, Any], name: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != name}


def build_cross_topic_protocol(
    *,
    provider_config_path: Path,
    source_commit: str,
) -> dict[str, Any]:
    provider_config = json.loads(provider_config_path.read_text(encoding="utf-8"))
    missing = [provider for provider in PROVIDERS if provider not in provider_config]
    if missing:
        raise ValueError(f"provider config missing: {missing}")
    tasks: list[dict[str, Any]] = []
    for topic in TOPICS:
        for provider in PROVIDERS:
            config = provider_config[provider]
            task = {
                "task_id": f"{topic['topic_id']}-{provider}-seed{SEED}",
                "topic_id": topic["topic_id"],
                "topic": topic["title"],
                "provider": provider,
                "model_id": config["model_id"],
                "api_key_env": config["api_key_env"],
                "seed": SEED,
                "status": (
                    "blocked_budget" if provider == "deepseek" else "pending_authorization"
                ),
                "output_relpath": f"{topic['topic_id']}/{provider}/seed{SEED}",
                "source_commit": source_commit,
            }
            task["input_sha256"] = _canonical_sha256(task)
            tasks.append(task)
    protocol: dict[str, Any] = {
        "schema_version": 1,
        "protocol_id": "cross-topic-s4-v1",
        "source_commit": source_commit,
        "provider_config_sha256": sha256(
            provider_config_path.read_bytes()
        ).hexdigest().upper(),
        "topics": [dict(topic) for topic in TOPICS],
        "providers": list(PROVIDERS),
        "seed": SEED,
        "prompt_template": PROMPT_TEMPLATE,
        "topic_specific_templates": "forbidden",
        "prior_result_reuse": "forbidden",
        "required_artifacts": list(REQUIRED_ARTIFACTS),
        "failure_policy": "write_failure_report_never_fabricate_paper",
        "tasks": tasks,
        "tasks_sha256": _canonical_sha256(tasks),
    }
    protocol["protocol_sha256"] = _canonical_sha256(protocol)
    return protocol


def validate_cross_topic_protocol(
    protocol: dict[str, Any],
    *,
    output_root: Path,
    selected_output_relpaths: set[str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    existing_outputs: list[str] = []
    tasks = protocol.get("tasks")
    if not isinstance(tasks, list):
        return {"valid": False, "errors": ["tasks_missing"], "existing_outputs": []}

    expected_ids = {
        f"{topic['topic_id']}-{provider}-seed{SEED}"
        for topic in TOPICS
        for provider in PROVIDERS
    }
    actual_ids: set[object] = set()
    for task in tasks:
        if not isinstance(task, dict):
            errors.append("task_invalid")
            continue
        actual_ids.add(task.get("task_id"))
        provider = task.get("provider")
        expected_status = (
            "blocked_budget" if provider == "deepseek" else "pending_authorization"
        )
        if task.get("status") != expected_status:
            errors.append("provider_status_invalid")
        frozen_input = _without_hash(task, "input_sha256")
        if task.get("input_sha256") != _canonical_sha256(frozen_input):
            errors.append("task_input_hash_mismatch")
        output_relpath = task.get("output_relpath")
        should_check_output = (
            selected_output_relpaths is None
            or output_relpath in selected_output_relpaths
        )
        if (
            isinstance(output_relpath, str)
            and should_check_output
            and (output_root / output_relpath).exists()
        ):
            existing_outputs.append(output_relpath)

    if len(tasks) != 9 or actual_ids != expected_ids:
        errors.append("cross_topic_protocol_incomplete")
    if protocol.get("topics") != [dict(topic) for topic in TOPICS]:
        errors.append("topic_set_invalid")
    if protocol.get("providers") != list(PROVIDERS):
        errors.append("provider_set_invalid")
    if protocol.get("prompt_template") != PROMPT_TEMPLATE:
        errors.append("prompt_template_invalid")
    if protocol.get("topic_specific_templates") != "forbidden":
        errors.append("topic_specific_template_allowed")
    if protocol.get("prior_result_reuse") != "forbidden":
        errors.append("prior_result_reuse_allowed")
    if protocol.get("required_artifacts") != list(REQUIRED_ARTIFACTS):
        errors.append("artifact_contract_invalid")
    if protocol.get("tasks_sha256") != _canonical_sha256(tasks):
        errors.append("tasks_hash_mismatch")
    if protocol.get("protocol_sha256") != _canonical_sha256(
        _without_hash(protocol, "protocol_sha256")
    ):
        errors.append("protocol_hash_mismatch")
    if existing_outputs:
        errors.append("cross_topic_output_exists")
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


def freeze_cross_topic_protocol(
    *,
    provider_config_path: Path,
    source_commit: str,
    output_root: Path,
    manifest_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    for path in (manifest_path, report_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite frozen evidence: {path}")
    protocol = build_cross_topic_protocol(
        provider_config_path=provider_config_path,
        source_commit=source_commit,
    )
    report = validate_cross_topic_protocol(protocol, output_root=output_root)
    if not report["valid"]:
        raise ValueError(f"cross-topic preflight failed: {report['errors']}")
    statuses = Counter(task["status"] for task in protocol["tasks"])
    report.update(
        {
            "mode": "offline_preflight",
            "model_api_calls": 0,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": protocol["protocol_sha256"],
            "task_counts": {
                "total": len(protocol["tasks"]),
                "pending_authorization": statuses["pending_authorization"],
                "blocked_budget": statuses["blocked_budget"],
            },
            "output_root": str(output_root),
        }
    )
    _write_json_exclusive(manifest_path, protocol)
    _write_json_exclusive(report_path, report)
    return report


__all__ = [
    "build_cross_topic_protocol",
    "freeze_cross_topic_protocol",
    "validate_cross_topic_protocol",
]
