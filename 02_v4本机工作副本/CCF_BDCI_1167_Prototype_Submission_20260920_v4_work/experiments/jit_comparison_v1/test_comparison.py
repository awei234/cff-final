import json
from pathlib import Path

from run_comparison import ARMS, SEEDS, run_comparison


def test_comparison_runs_all_arms_and_seeds(tmp_path: Path):
    result = run_comparison(tmp_path / "results")
    assert result["arms"] == list(ARMS)
    assert result["seeds"] == list(SEEDS)
    assert len(result["results"]) == 12
    jit = [row for row in result["results"] if row["arm"] == "jit-constrained"]
    assert len(jit) == 3
    assert all(row["manifest"]["profile"] for row in jit)
    assert result["gate"]["all_passed"] is True
    assert all(row["metrics"]["evidence_coverage_rate"]["value"] == 1.0 for row in jit)
    assert all(row["metrics"]["misquote_rate"]["status"] == "not_measured_no_quoted_sources" for row in jit)
    assert json.loads((tmp_path / "results" / "comparison_results.json").read_text(encoding="utf-8"))["results"]
