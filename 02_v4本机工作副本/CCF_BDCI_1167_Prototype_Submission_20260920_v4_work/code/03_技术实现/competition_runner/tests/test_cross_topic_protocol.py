from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

import pytest

from competition_runner.cross_topic import (
    build_cross_topic_protocol,
    freeze_cross_topic_protocol,
    validate_cross_topic_protocol,
)


PROVIDERS = {
    "glm": {
        "api_base": "https://example.invalid/glm",
        "api_key_env": "GLM_KEY",
        "model_id": "glm-model",
    },
    "qwen": {
        "api_base": "https://example.invalid/qwen",
        "api_key_env": "QWEN_KEY",
        "model_id": "qwen-model",
    },
    "deepseek": {
        "api_base": "https://example.invalid/deepseek",
        "api_key_env": "DEEPSEEK_KEY",
        "model_id": "deepseek-model",
    },
}


def _provider_config(tmp_path):
    path = tmp_path / "providers.json"
    path.write_text(json.dumps(PROVIDERS), encoding="utf-8")
    return path


def test_protocol_freezes_three_topics_and_nine_budget_aware_tasks(tmp_path):
    """Dropping a topic/provider or unlocking DeepSeek must invalidate the formal protocol."""
    protocol = build_cross_topic_protocol(
        provider_config_path=_provider_config(tmp_path),
        source_commit="a" * 40,
    )

    assert protocol["topics"] == [
        {"topic_id": "context-engineering", "title": "Agent上下文工程"},
        {"topic_id": "memory-engine", "title": "Agent记忆引擎"},
        {"topic_id": "self-evolution", "title": "Agent自演进"},
    ]
    assert len(protocol["tasks"]) == 9
    assert Counter(task["status"] for task in protocol["tasks"]) == {
        "pending_authorization": 6,
        "blocked_budget": 3,
    }
    assert {
        task["provider"]
        for task in protocol["tasks"]
        if task["status"] == "blocked_budget"
    } == {"deepseek"}
    assert {task["seed"] for task in protocol["tasks"]} == {42}


def test_protocol_uses_one_topic_parameterized_contract_without_copied_results(tmp_path):
    """A topic-specific template or inherited paper data would defeat the generalization test."""
    protocol = build_cross_topic_protocol(
        provider_config_path=_provider_config(tmp_path),
        source_commit="b" * 40,
    )

    assert protocol["prompt_template"] == (
        "Run the unified research pipeline for topic: {topic}. "
        "Do not reuse prior paper claims or results; preserve failures as evidence."
    )
    assert protocol["prior_result_reuse"] == "forbidden"
    assert protocol["topic_specific_templates"] == "forbidden"
    assert protocol["required_artifacts"] == [
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
    ]


def test_validator_rejects_tampering_and_existing_outputs(tmp_path):
    """Changing a frozen task or reusing a run directory must fail before execution."""
    protocol = build_cross_topic_protocol(
        provider_config_path=_provider_config(tmp_path),
        source_commit="c" * 40,
    )
    protocol["tasks"][0]["topic"] = "changed after freeze"
    output_root = tmp_path / "runs"
    (output_root / protocol["tasks"][1]["output_relpath"]).mkdir(parents=True)

    report = validate_cross_topic_protocol(protocol, output_root=output_root)

    assert report["valid"] is False
    assert report["errors"] == [
        "cross_topic_output_exists",
        "protocol_hash_mismatch",
        "task_input_hash_mismatch",
        "tasks_hash_mismatch",
    ]
    assert report["existing_outputs"] == [protocol["tasks"][1]["output_relpath"]]


def test_freeze_writes_zero_call_evidence_once(tmp_path):
    """A second freeze must not overwrite the evidence used to authorize later live runs."""
    manifest = tmp_path / "cross_topic_protocol.json"
    report_path = tmp_path / "cross_topic_preflight.json"
    output_root = tmp_path / "formal_runs"

    report = freeze_cross_topic_protocol(
        provider_config_path=_provider_config(tmp_path),
        source_commit="d" * 40,
        output_root=output_root,
        manifest_path=manifest,
        report_path=report_path,
    )

    assert report["valid"] is True
    assert report["mode"] == "offline_preflight"
    assert report["model_api_calls"] == 0
    assert report["task_counts"] == {
        "total": 9,
        "pending_authorization": 6,
        "blocked_budget": 3,
    }
    assert manifest.is_file()
    assert report_path.is_file()
    assert not output_root.exists()
    frozen = manifest.read_bytes()
    preflight = report_path.read_bytes()

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        freeze_cross_topic_protocol(
            provider_config_path=_provider_config(tmp_path),
            source_commit="d" * 40,
            output_root=output_root,
            manifest_path=manifest,
            report_path=report_path,
        )

    assert manifest.read_bytes() == frozen
    assert report_path.read_bytes() == preflight


def test_freeze_cli_creates_only_manifest_and_zero_call_report(tmp_path):
    """The operator command must remain offline and refuse a second run."""
    script = Path(__file__).resolve().parents[1] / "freeze_cross_topic_protocol.py"
    provider_config = _provider_config(tmp_path)
    manifest = tmp_path / "protocol.json"
    report = tmp_path / "preflight.json"
    output_root = tmp_path / "formal_runs"
    command = [
        sys.executable,
        str(script),
        "--provider-config",
        str(provider_config),
        "--source-commit",
        "e" * 40,
        "--output-root",
        str(output_root),
        "--manifest",
        str(manifest),
        "--report",
        str(report),
    ]

    first = subprocess.run(command, capture_output=True, text=True, shell=False)
    second = subprocess.run(command, capture_output=True, text=True, shell=False)

    assert first.returncode == 0
    assert json.loads(first.stdout)["model_api_calls"] == 0
    assert second.returncode == 2
    assert "refusing to overwrite" in second.stderr
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "preflight.json",
        "protocol.json",
        "providers.json",
    ]
