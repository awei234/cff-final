import json
from pathlib import Path
import sys

import pytest

from aggregate_results import main as aggregate_main
from ucr_benchmark.aggregate import aggregate_runs


def _write_result(root: Path, arm: str, seed: int, numerator: int, denominator: int):
    path = root / arm / f"seed{seed}" / "results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "arm": arm,
                "seed": seed,
                "metrics": {
                    "UCR": {
                        "value": round(numerator / denominator, 4),
                        "numerator": numerator,
                        "denominator": denominator,
                        "activated": True,
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def _write_not_applicable(root: Path, arm: str, seed: int):
    path = root / arm / f"seed{seed}" / "results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "arm": arm,
                "seed": seed,
                "metrics": {
                    "UCR": {
                        "value": None,
                        "numerator": 0,
                        "denominator": 0,
                        "supported": 0,
                        "unexecuted": 0,
                        "indeterminate": 0,
                        "activated": False,
                        "status": "not_applicable",
                        "reason": "no_detectable_claims",
                    }
                },
                "rail": {"attempts": 1, "accepted": False},
            }
        ),
        encoding="utf-8",
    )


def test_aggregation_requires_complete_arms_and_computes_paired_differences(tmp_path: Path):
    for seed, num in zip((42, 43, 44), (2, 1, 3)):
        _write_result(tmp_path, "no-rail", seed, num, 4)
    for seed, num in zip((42, 43, 44), (1, 1, 0)):
        _write_result(tmp_path, "prompt-only", seed, num, 4)
    for seed in (42, 43, 44):
        _write_result(tmp_path, "full-rail", seed, 0, 4)

    summary = aggregate_runs(tmp_path)

    assert summary["complete"] is True
    assert summary["all_dimensions_activated"] is True
    assert summary["arms"]["no-rail"]["UCR"]["mean"] == 0.5
    assert summary["arms"]["no-rail"]["UCR"]["total_numerator"] == 6
    assert summary["arms"]["no-rail"]["UCR"]["total_denominator"] == 12
    assert summary["paired_differences"]["full-rail_minus_no-rail"] == [-0.5, -0.25, -0.75]


def test_aggregation_rejects_missing_seed_and_unactivated_ucr(tmp_path: Path):
    _write_result(tmp_path, "no-rail", 42, 1, 2)
    with pytest.raises(ValueError, match="missing result"):
        aggregate_runs(tmp_path)

    for arm in ("no-rail", "prompt-only", "full-rail"):
        for seed in (42, 43, 44):
            _write_result(tmp_path, arm, seed, 0, 1)
    result_path = tmp_path / "full-rail" / "seed44" / "results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["metrics"]["UCR"].update(value=None, denominator=0, activated=False)
    result_path.write_text(json.dumps(result), encoding="utf-8")

    with pytest.raises(ValueError, match="UCR dimension is not activated"):
        aggregate_runs(tmp_path)


def test_formal_aggregation_uses_explicit_seeds_without_treating_not_applicable_as_zero(
    tmp_path: Path,
):
    seeds = (42, 43, 44, 45)
    for arm in ("no-rail", "prompt-only", "full-rail"):
        _write_not_applicable(tmp_path, arm, 42)
        _write_result(tmp_path, arm, 43, 1, 4)
        _write_result(tmp_path, arm, 44, 2, 4)
        _write_result(tmp_path, arm, 45, 3, 4)

    summary = aggregate_runs(tmp_path, seeds=seeds, allow_not_applicable=True)

    ucr = summary["arms"]["full-rail"]["UCR"]
    assert summary["complete"] is True
    assert summary["all_dimensions_activated"] is False
    assert summary["arms"]["full-rail"]["seeds"] == [42, 43, 44, 45]
    assert ucr["per_seed"] == [None, 0.25, 0.5, 0.75]
    assert ucr["activated_seed_count"] == 3
    assert ucr["not_applicable_seed_count"] == 1
    assert ucr["mean"] == 0.5
    assert ucr["total_numerator"] == 6
    assert ucr["total_denominator"] == 12
    assert ucr["pooled_value"] == 0.5
    assert ucr["confidence_interval_95"]["method"] == "wilson"
    assert summary["paired_differences"]["full-rail_minus_no-rail"] == [
        None,
        0.0,
        0.0,
        0.0,
    ]
    assert summary["paired_comparable_seed_counts"][
        "full-rail_minus_no-rail"
    ] == 3


def test_aggregate_cli_accepts_explicit_formal_seed_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    seeds = (42, 43, 44, 45)
    for arm in ("no-rail", "prompt-only", "full-rail"):
        _write_not_applicable(tmp_path, arm, 42)
        for seed in seeds[1:]:
            _write_result(tmp_path, arm, seed, 1, 4)
    output = tmp_path / "formal_summary.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "aggregate_results.py",
            str(tmp_path),
            "--output",
            str(output),
            "--seeds",
            "42,43,44,45",
            "--allow-not-applicable",
        ],
    )

    assert aggregate_main() == 0

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["arms"]["no-rail"]["seeds"] == [42, 43, 44, 45]
    assert summary["arms"]["no-rail"]["UCR"]["not_applicable_seed_count"] == 1
