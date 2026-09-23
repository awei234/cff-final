import json
from pathlib import Path

from competition_runner.harness.archive import archive_run
from competition_runner.harness.selector import select_harness
from competition_runner.harness.validator import validate_manifest


def test_valid_evidence_manifest_passes_validation():
    manifest = select_harness({"requires_evidence": True})
    result = validate_manifest(manifest)
    assert result.valid is True
    assert result.manifest["profile"] == "evidence_first"


def test_invalid_tool_or_budget_falls_back_to_full_rail():
    result = validate_manifest({
        "profile": "evidence_first",
        "memory_mode": "structured_evidence",
        "planning_mode": "sequential_verify",
        "enabled_tools": ["shell"],
        "max_provider_calls": 999,
        "max_retries": 1,
        "selection_reason": "bad input",
    })
    assert result.valid is False
    assert result.manifest["profile"] == "full-rail"
    assert result.fallback_reason


def test_archive_saves_manifest_cost_latency_evidence_and_hash(tmp_path: Path):
    manifest = select_harness({"requires_evidence": True})
    output = archive_run(
        tmp_path,
        manifest=manifest,
        validation={"valid": True},
        metrics={"cost": 0.12, "latency_ms": 330},
        evidence=[{"evidence_id": "e1", "sha256": "abc"}],
    )
    data = json.loads((output / "harness_archive.json").read_text(encoding="utf-8"))
    assert data["manifest"] == manifest
    assert data["metrics"]["cost"] == 0.12
    assert data["evidence"][0]["evidence_id"] == "e1"
    assert data["archive_sha256"]
