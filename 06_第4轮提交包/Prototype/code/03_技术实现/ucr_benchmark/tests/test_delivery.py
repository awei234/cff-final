from pathlib import Path

from ucr_benchmark.jit_delivery import verify_jit_comparison


def test_complete_project_delivery_is_self_consistent():
    work_copy_root = Path(__file__).resolve().parents[4]
    results_root = work_copy_root / "evidence" / "jit_comparison_v2_final"
    assert verify_jit_comparison(results_root) == []
