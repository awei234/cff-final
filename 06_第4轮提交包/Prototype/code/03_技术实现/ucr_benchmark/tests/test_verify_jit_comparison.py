from __future__ import annotations

import json
from pathlib import Path

from ucr_benchmark.aggregate import aggregate_runs
from ucr_benchmark.experiment import ARMS, FixturePolicyAdapter, run_one
from ucr_benchmark.schema import write_json


def _build_four_arm_fixture(root: Path) -> None:
    for arm in ARMS:
        for seed in (42, 43, 44):
            run_one(arm, seed, FixturePolicyAdapter(), root)
    write_json(root / "summary.json", aggregate_runs(root))


def test_four_arm_verifier_accepts_complete_auditable_batch(tmp_path: Path):
    try:
        from ucr_benchmark.jit_delivery import verify_jit_comparison
    except ImportError as exc:
        raise AssertionError("four-arm JIT delivery verifier is required") from exc
    _build_four_arm_fixture(tmp_path)

    assert verify_jit_comparison(tmp_path) == []


def test_four_arm_verifier_rejects_tampered_harness_archive(tmp_path: Path):
    from ucr_benchmark.jit_delivery import verify_jit_comparison

    _build_four_arm_fixture(tmp_path)
    archive_path = (
        tmp_path
        / "jit-constrained"
        / "seed42"
        / "harness"
        / "harness_archive.json"
    )
    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    archive["metrics"]["provider_call_count"] = 99
    archive_path.write_text(json.dumps(archive), encoding="utf-8")

    errors = verify_jit_comparison(tmp_path)

    assert "provenance mismatch: jit-constrained/seed42/harness/harness_archive.json" in errors
    assert "harness archive hash mismatch: jit-constrained/seed42" in errors
