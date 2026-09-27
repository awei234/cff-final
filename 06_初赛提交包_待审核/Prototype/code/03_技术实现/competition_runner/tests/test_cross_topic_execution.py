from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from competition_runner.cross_topic_execution import (
    CrossTopicExecutionError,
    dry_run_cross_topic_protocol,
)


BASE = Path(__file__).resolve().parents[1]
FROZEN_PROTOCOL = BASE / "config" / "cross_topic_protocol_s4_v1.json"
PROVIDER_CONFIG = BASE / "config" / "providers.json"


def _copy_json(source: Path, destination: Path) -> Path:
    destination.write_bytes(source.read_bytes())
    return destination


def test_dry_run_classifies_all_frozen_tasks_without_outputs_or_credentials(tmp_path):
    """A dry-run that executes a task, reads a key, or unlocks DeepSeek breaks the budget gate."""
    output_root = tmp_path / "formal_runs"
    report_path = tmp_path / "dry_run.json"

    report = dry_run_cross_topic_protocol(
        protocol_path=FROZEN_PROTOCOL,
        provider_config_path=PROVIDER_CONFIG,
        output_root=output_root,
        report_path=report_path,
    )

    assert report["mode"] == "offline_dry_run"
    assert report["valid"] is True
    assert report["model_api_calls"] == 0
    assert report["api_key_reads"] == 0
    assert report["results_written"] == 0
    assert report["live_execution_enabled"] is False
    assert report["required_artifact_count"] == 14
    assert report["task_counts"] == {
        "total": 9,
        "eligible_not_executed": 6,
        "blocked_budget": 3,
    }
    assert len(report["tasks"]) == 9
    assert {
        task["provider"]
        for task in report["tasks"]
        if task["dry_run_status"] == "blocked_budget"
    } == {"deepseek"}
    assert not output_root.exists()
    assert json.loads(report_path.read_text(encoding="utf-8")) == report


def test_dry_run_rejects_provider_drift_before_writing_report(tmp_path):
    """Changing a frozen model must not silently redirect a later paid task."""
    providers = json.loads(PROVIDER_CONFIG.read_text(encoding="utf-8"))
    providers["qwen"]["model_id"] = "changed-model"
    changed_config = tmp_path / "providers.json"
    changed_config.write_text(json.dumps(providers), encoding="utf-8")
    report_path = tmp_path / "dry_run.json"

    with pytest.raises(CrossTopicExecutionError) as exc:
        dry_run_cross_topic_protocol(
            protocol_path=FROZEN_PROTOCOL,
            provider_config_path=changed_config,
            output_root=tmp_path / "formal_runs",
            report_path=report_path,
        )

    assert exc.value.code == "provider_config_drift"
    assert not report_path.exists()


def test_dry_run_rejects_protocol_tampering_before_writing_report(tmp_path):
    """A changed task must fail its frozen hashes instead of entering the eligible queue."""
    protocol = json.loads(FROZEN_PROTOCOL.read_text(encoding="utf-8"))
    protocol["tasks"][0]["topic"] = "changed after freeze"
    changed_protocol = tmp_path / "protocol.json"
    changed_protocol.write_text(json.dumps(protocol), encoding="utf-8")
    report_path = tmp_path / "dry_run.json"

    with pytest.raises(CrossTopicExecutionError) as exc:
        dry_run_cross_topic_protocol(
            protocol_path=changed_protocol,
            provider_config_path=PROVIDER_CONFIG,
            output_root=tmp_path / "formal_runs",
            report_path=report_path,
        )

    assert exc.value.code == "protocol_invalid"
    assert "task_input_hash_mismatch" in str(exc.value)
    assert not report_path.exists()


def test_dry_run_rejects_any_existing_formal_output(tmp_path):
    """Reusing even one frozen output path would overwrite or mix formal evidence."""
    output_root = tmp_path / "formal_runs"
    occupied = output_root / "memory-engine" / "glm" / "seed42"
    occupied.mkdir(parents=True)
    marker = occupied / "historical.txt"
    marker.write_text("keep", encoding="utf-8")
    report_path = tmp_path / "dry_run.json"

    with pytest.raises(CrossTopicExecutionError) as exc:
        dry_run_cross_topic_protocol(
            protocol_path=FROZEN_PROTOCOL,
            provider_config_path=PROVIDER_CONFIG,
            output_root=output_root,
            report_path=report_path,
        )

    assert exc.value.code == "formal_output_exists"
    assert marker.read_text(encoding="utf-8") == "keep"
    assert not report_path.exists()


def test_dry_run_report_is_exclusive_and_unchanged_on_second_run(tmp_path):
    """A rerun must not replace the report used to authorize future live work."""
    report_path = tmp_path / "dry_run.json"
    args = {
        "protocol_path": FROZEN_PROTOCOL,
        "provider_config_path": PROVIDER_CONFIG,
        "output_root": tmp_path / "formal_runs",
        "report_path": report_path,
    }
    dry_run_cross_topic_protocol(**args)
    frozen = report_path.read_bytes()

    with pytest.raises(CrossTopicExecutionError) as exc:
        dry_run_cross_topic_protocol(**args)

    assert exc.value.code == "evidence_exists"
    assert report_path.read_bytes() == frozen


def test_dry_run_cli_writes_one_zero_call_report_and_refuses_overwrite(tmp_path):
    """The operator CLI must expose the same fail-closed offline behavior."""
    script = BASE / "run_cross_topic_protocol.py"
    report_path = tmp_path / "dry_run.json"
    output_root = tmp_path / "formal_runs"
    command = [
        sys.executable,
        str(script),
        "--dry-run",
        "--protocol",
        str(FROZEN_PROTOCOL),
        "--provider-config",
        str(PROVIDER_CONFIG),
        "--output-root",
        str(output_root),
        "--report",
        str(report_path),
    ]

    first = subprocess.run(command, capture_output=True, text=True, shell=False)
    second = subprocess.run(command, capture_output=True, text=True, shell=False)

    assert first.returncode == 0
    assert json.loads(first.stdout)["model_api_calls"] == 0
    assert second.returncode == 2
    assert "evidence_exists" in second.stderr
    assert not output_root.exists()
