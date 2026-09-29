from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE.parents[1]
WORK_COPY_ROOT = BASE.parents[2]
JIT_RESULTS = WORK_COPY_ROOT / "demo_runs" / "jit_comparison_v2_final"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_checked_out_scenarios_preserve_frozen_bytes() -> None:
    manifest = json.loads(
        (BASE / "config" / "formal_experiment_s3_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert _sha256(BASE / "config" / "scenarios.json").upper() == manifest[
        "scenario_sha256"
    ]


def test_git_attributes_disable_eol_conversion_for_integrity_bound_files() -> None:
    attributes = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "03_技术实现/ucr_benchmark/config/scenarios.json -text" in attributes
    assert (
        "03_技术实现/ucr_benchmark/results/**/model_output.txt -text"
        in attributes
    )


def test_pytest_basetemp_does_not_require_an_untracked_parent_directory() -> None:
    pytest_ini = (BASE / "pytest.ini").read_text(encoding="utf-8")
    assert "--basetemp=.pytest_tmp\n" in pytest_ini
    assert "--basetemp=.pytest_tmp/current" not in pytest_ini


@pytest.mark.parametrize(
    ("arm", "seed"),
    [
        (arm, seed)
        for arm in ("no-rail", "prompt-only", "full-rail", "jit-constrained")
        for seed in (42, 43, 44)
    ],
)
def test_checked_out_model_output_preserves_provenance_bytes(
    arm: str, seed: int
) -> None:
    run_dir = JIT_RESULTS / arm / f"seed{seed}"
    provenance = json.loads(
        (run_dir / "provenance.json").read_text(encoding="utf-8")
    )
    assert _sha256(run_dir / "model_output.txt") == provenance["files"][
        "model_output.txt"
    ]
