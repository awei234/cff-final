import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "demo_runs" / "research_matrix_live_20260924_authorized"
TOPICS = ("context-engineering", "memory-engine", "self-evolution")
EXCLUDED = ["claim-002", "claim-003", "claim-005", "claim-007", "claim-009"]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_claim_review_release_gate():
    audit = read_json(RUN / "claim_review_audit.json")
    assert audit["overall_passed"] is True
    assert audit["expected_excluded_claims"] == EXCLUDED
    for topic in TOPICS:
        review = read_json(RUN / topic / "review.json")
        report = read_json(RUN / topic / "report.json")
        assert review["unsupported_claims"] == EXCLUDED
        assert report["unsupported_claims"] == EXCLUDED
        assert review["allow_paper"] is True
        assert set(("claim-018", "claim-019", "claim-020")).issubset(
            set(review["paper_eligible_claims"])
        )


def test_approved_background_sources_are_allowed():
    for topic in TOPICS:
        ledger = read_json(RUN / topic / "claim_ledger.json")
        materials = read_json(RUN / topic / "research_materials.json")
        sources = {source["source_id"]: source for source in materials["sources"]}
        claims = {claim["claim_id"]: claim for claim in ledger["claims"]}
        for claim_id in ("claim-018", "claim-019", "claim-020"):
            claim = claims[claim_id]
            assert claim["status"] == "supported"
            for ref in claim["source_refs"]:
                assert sources[ref["source_id"]]["citation_allowed"] is True


def test_harness_archives_exist_for_all_topics():
    for topic in TOPICS:
        assert (RUN / topic / "harness_manifest.json").exists()
        assert (RUN / topic / "harness_validation.json").exists()
        assert (RUN / topic / "harness" / "harness_archive.json").exists()
