from pathlib import Path

import pytest

from competition_runner.provenance import ProvenanceError, SourceRegistry


def test_unapproved_source_cannot_back_a_claim(tmp_path: Path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"answer": 42}', encoding="utf-8")
    registry = SourceRegistry()
    registry.register("src-1", "https://example.test/paper", status="verified")

    with pytest.raises(ProvenanceError, match="approved"):
        registry.add_claim("claim-1", "answer is 42", "src-1", evidence, "/answer")


def test_approved_claim_records_locator_and_hash(tmp_path: Path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"answer": 42}', encoding="utf-8")
    registry = SourceRegistry()
    registry.register("src-1", "https://example.test/paper", status="verified")
    registry.approve("src-1", reviewer="human")

    claim = registry.add_claim("claim-1", "answer is 42", "src-1", evidence, "/answer")

    assert claim["status"] == "approved_for_claim"
    assert claim["locator"] == "/answer"
    assert registry.verify_claim("claim-1") is True


def test_claim_verification_detects_tampered_artifact(tmp_path: Path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text("original", encoding="utf-8")
    registry = SourceRegistry()
    registry.register("src-1", "https://example.test/paper", status="verified")
    registry.approve("src-1", reviewer="human")
    registry.add_claim("claim-1", "text", "src-1", evidence, "line:1")
    evidence.write_text("tampered", encoding="utf-8")

    with pytest.raises(ProvenanceError, match="hash_mismatch"):
        registry.verify_claim("claim-1")
