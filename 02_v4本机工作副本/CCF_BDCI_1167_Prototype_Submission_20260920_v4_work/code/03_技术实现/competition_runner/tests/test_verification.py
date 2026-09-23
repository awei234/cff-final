from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from competition_runner.artifact_contract import HASHED_ARTIFACTS, REQUIRED_ARTIFACTS
from competition_runner.verification import verify_run


RUN_ID = "glm-42-0123456789ab-20260827T120000Z"
TIMESTAMP = "2026-08-27T12:00:00+00:00"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_valid_run(run_dir: Path) -> Path:
    run_dir.mkdir()
    manifest = {
        "schema_version": "1.0",
        "run_id": RUN_ID,
        "topic": "Agent context engineering",
        "provider": "glm",
        "model": "glm-fixture",
        "seed": 42,
        "mode": "fixture",
        "created_at_utc": TIMESTAMP,
        "status": "completed",
        "required_artifacts": list(REQUIRED_ARTIFACTS),
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    (run_dir / "prompt.txt").write_text("Study Agent context engineering.\n", encoding="utf-8")
    event = {
        "event_id": "event-1",
        "operation_id": "operation-1",
        "tool": "fixture_generator",
        "status": "success",
        "timestamp_utc": TIMESTAMP,
        "evidence": {"mode": "fixture"},
    }
    (run_dir / "tool_trace.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    _write_json(
        run_dir / "results.json",
        {
            "schema_version": "1.0",
            "run_id": RUN_ID,
            "status": "fixture_completed",
            "claims": [],
            "measurements": [],
        },
    )
    (run_dir / "paper.tex").write_text("% fixture only\n\\documentclass{article}\n", encoding="utf-8")
    (run_dir / "paper.pdf").write_bytes(b"%PDF-1.4\nfixture\n%%EOF\n")
    _write_json(
        run_dir / "resource.json",
        {
            "schema_version": "1.0",
            "run_id": RUN_ID,
            "token_usage": None,
            "duration_seconds": None,
            "cost": None,
            "measurement_status": "not_applicable",
        },
    )
    _write_json(
        run_dir / "provenance.json",
        {
            "schema_version": "1.0",
            "run_id": RUN_ID,
            "source_commit": "a" * 40,
            "source_commit_status": "available",
            "generator": {"name": "fixture", "mode": "fixture"},
            "artifact_hashes": {name: _sha256(run_dir / name) for name in HASHED_ARTIFACTS},
        },
    )
    _write_json(
        run_dir / "verification_report.json",
        {
            "schema_version": "1.0",
            "run_id": RUN_ID,
            "valid": True,
            "checks": [],
            "errors": [],
            "verified_at_utc": TIMESTAMP,
            "run_manifest_sha256": _sha256(run_dir / "run_manifest.json"),
            "provenance_sha256": _sha256(run_dir / "provenance.json"),
        },
    )
    return run_dir


def test_verify_run_accepts_a_consistent_run(tmp_path):
    """Removing any required verification check must stop a complete run from proving validity."""
    run_dir = _write_valid_run(tmp_path / "run-001")

    result = verify_run(run_dir)

    assert result.valid is True
    assert result.run_id == RUN_ID
    assert result.errors == ()
    assert result.run_manifest_sha256 == _sha256(run_dir / "run_manifest.json")
    assert result.provenance_sha256 == _sha256(run_dir / "provenance.json")


def _mutate_run(run_dir: Path, mutation: str) -> None:
    if mutation == "remove_results":
        (run_dir / "results.json").unlink()
    elif mutation == "change_run_id":
        results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
        results["run_id"] = "different-run"
        _write_json(run_dir / "results.json", results)
    elif mutation == "change_prompt":
        (run_dir / "prompt.txt").write_text("tampered\n", encoding="utf-8")
    elif mutation == "truncate_pdf":
        (run_dir / "paper.pdf").write_bytes(b"not a pdf")
    elif mutation == "remove_field":
        results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
        del results["claims"]
        _write_json(run_dir / "results.json", results)
    else:
        raise AssertionError(f"unknown test mutation: {mutation}")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("remove_results", "artifact_missing"),
        ("change_run_id", "run_identity_mismatch"),
        ("change_prompt", "hash_mismatch"),
        ("truncate_pdf", "pdf_invalid"),
        ("remove_field", "artifact_invalid"),
    ],
)
def test_verify_run_rejects_contract_breakage(tmp_path, mutation, code):
    """Each protected contract boundary must produce a stable rejection code."""
    run_dir = _write_valid_run(tmp_path / "run-001")
    _mutate_run(run_dir, mutation)

    result = verify_run(run_dir)

    assert result.valid is False
    assert code in {issue.code for issue in result.errors}


def test_verify_run_reports_an_unknown_file(tmp_path):
    """Untracked extra evidence must not pass as part of the frozen artifact set."""
    run_dir = _write_valid_run(tmp_path / "run-001")
    (run_dir / "untracked.txt").write_text("unexpected\n", encoding="utf-8")

    result = verify_run(run_dir)

    assert result.valid is False
    assert "artifact_unknown" in {issue.code for issue in result.errors}


def test_verify_run_is_read_only_and_reports_a_stale_stored_report(tmp_path):
    """Reverification must expose stale identity evidence without rewriting history."""
    run_dir = _write_valid_run(tmp_path / "run-001")
    provenance_path = run_dir / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["generator"]["version"] = "changed"
    _write_json(provenance_path, provenance)
    before = {path.name: _sha256(path) for path in run_dir.iterdir() if path.is_file()}

    first = verify_run(run_dir)
    second = verify_run(run_dir)
    after = {path.name: _sha256(path) for path in run_dir.iterdir() if path.is_file()}

    assert first.valid is False
    assert second.valid is False
    assert "verification_report_stale" in {issue.code for issue in first.errors}
    assert after == before
