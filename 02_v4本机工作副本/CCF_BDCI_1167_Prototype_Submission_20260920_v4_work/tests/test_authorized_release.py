import json
import shutil
from pathlib import Path

from verify_authorized_release import verify_release


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "demo_runs" / "research_matrix_live_20260924_authorized"
JIT = ROOT / "demo_runs" / "jit_comparison_v1_final"


def test_authorized_run_and_jit_archive_pass():
    result = verify_release(RUN, JIT)
    assert result["release_ready"] is True, result["errors"]
    assert result["topics_checked"] == 3
    assert result["pdfs_checked"] == 4
    assert result["jit_seed_arm_pairs_checked"] == 12


def test_revoked_paper_approval_blocks_release(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(RUN, run)
    path = run / "context-engineering" / "review.json"
    review = json.loads(path.read_text(encoding="utf-8"))
    review["allow_paper"] = False
    path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")

    result = verify_release(run, JIT)
    assert result["release_ready"] is False
    assert any("context-engineering" in error and "allow_paper" in error for error in result["errors"])


def test_pdf_hash_tampering_blocks_release(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(RUN, run)
    with (run / "paper.pdf").open("ab") as output:
        output.write(b"tampered")

    result = verify_release(run, JIT)
    assert result["release_ready"] is False
    assert any("paper.pdf" in error and "hash" in error for error in result["errors"])


def test_missing_jit_arm_blocks_release(tmp_path):
    jit = tmp_path / "jit"
    shutil.copytree(JIT, jit)
    path = jit / "comparison_results.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["results"] = [row for row in data["results"] if not (row["seed"] == 44 and row["arm"] == "jit-constrained")]
    path.write_text(json.dumps(data), encoding="utf-8")

    result = verify_release(RUN, jit)
    assert result["release_ready"] is False
    assert any("jit-constrained" in error and "44" in error for error in result["errors"])


def test_jit_evidence_hash_tampering_blocks_release(tmp_path):
    jit = tmp_path / "jit"
    shutil.copytree(JIT, jit)
    path = jit / "seed-42" / "jit-constrained" / "tool_trace.jsonl"
    with path.open("ab") as output:
        output.write(b"tampered")

    result = verify_release(RUN, jit)
    assert result["release_ready"] is False
    assert any("JIT provenance hash mismatch" in error for error in result["errors"])


def test_jit_comparison_must_match_raw_result(tmp_path):
    jit = tmp_path / "jit"
    shutil.copytree(JIT, jit)
    path = jit / "seed-42" / "jit-constrained" / "results.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    result["metrics"]["UCR"]["value"] = 1.0
    path.write_text(json.dumps(result), encoding="utf-8")

    verification = verify_release(RUN, jit)
    assert verification["release_ready"] is False
    assert any("JIT comparison mismatch" in error for error in verification["errors"])
