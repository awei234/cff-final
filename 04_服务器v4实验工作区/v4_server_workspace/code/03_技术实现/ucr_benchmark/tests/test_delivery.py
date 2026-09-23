from pathlib import Path

from verify_delivery import verify_project


def test_complete_project_delivery_is_self_consistent():
    project_root = Path(__file__).resolve().parents[3]
    assert verify_project(project_root) == []
