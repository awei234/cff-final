from __future__ import annotations

import hashlib

import pytest

from competition_runner.artifact_contract import (
    REQUIRED_ARTIFACTS,
    load_json_object,
    load_jsonl,
    sha256_file,
)


def test_contract_lists_exactly_nine_required_artifacts():
    """Removing or renaming a formal artifact must break the public run contract."""
    assert REQUIRED_ARTIFACTS == (
        "run_manifest.json",
        "prompt.txt",
        "tool_trace.jsonl",
        "results.json",
        "paper.tex",
        "paper.pdf",
        "resource.json",
        "verification_report.json",
        "provenance.json",
    )


def test_sha256_file_hashes_exact_bytes(tmp_path):
    """Text normalization must not hide an artifact byte change."""
    artifact = tmp_path / "prompt.txt"
    artifact.write_bytes(b"topic\r\n")

    assert sha256_file(artifact) == hashlib.sha256(b"topic\r\n").hexdigest().upper()


def test_load_json_object_reports_a_missing_artifact(tmp_path):
    """A missing JSON document must become a stable issue rather than an exception."""
    value, issues = load_json_object(tmp_path / "results.json")

    assert value is None
    assert len(issues) == 1
    assert issues[0].code == "artifact_missing"
    assert issues[0].artifact == "results.json"


@pytest.mark.parametrize("contents", ["{", "[]"])
def test_load_json_object_rejects_invalid_documents(tmp_path, contents):
    """Malformed or non-object JSON must not enter contract validation."""
    path = tmp_path / "results.json"
    path.write_text(contents, encoding="utf-8")

    value, issues = load_json_object(path)

    assert value is None
    assert len(issues) == 1
    assert issues[0].code == "artifact_invalid"


def test_load_jsonl_rejects_a_non_object_line(tmp_path):
    """A scalar trace line must not be accepted as auditable tool evidence."""
    path = tmp_path / "tool_trace.jsonl"
    path.write_text('{"event_id":"event-1"}\n[]\n', encoding="utf-8")

    records, issues = load_jsonl(path)

    assert records == ()
    assert len(issues) == 1
    assert issues[0].code == "artifact_invalid_jsonl"
