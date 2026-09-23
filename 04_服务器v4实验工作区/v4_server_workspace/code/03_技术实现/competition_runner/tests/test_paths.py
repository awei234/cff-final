from __future__ import annotations

import json
from pathlib import Path

import pytest

from competition_runner.paths import PathConfigError, find_project_root, resolve_paths


RUNNER_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = RUNNER_DIR.parents[1]


def test_root_discovery_uses_anchor_instead_of_current_directory(tmp_path, monkeypatch):
    """Changing cwd must not redirect the formal project root."""
    monkeypatch.chdir(tmp_path)
    assert find_project_root(RUNNER_DIR) == REPO_ROOT.resolve()


def test_defaults_are_resolved_from_project_root(tmp_path, monkeypatch):
    """A wrong cwd must not produce machine-specific operational paths."""
    monkeypatch.chdir(tmp_path)
    resolved = resolve_paths(anchor=RUNNER_DIR)
    assert resolved.workspace_root == (REPO_ROOT / "workspace").resolve()
    assert resolved.output_root == (REPO_ROOT / "runs").resolve()
    assert resolved.experiment_script == (
        REPO_ROOT / "03_技术实现" / "ucr_benchmark" / "run_experiment.py"
    ).resolve()
    assert resolved.sources["project_root"] == "inferred"


def test_cli_override_wins_over_json_config(tmp_path):
    """An explicit runtime path must not be silently replaced by a file default."""
    config = tmp_path / "paths.json"
    config.write_text(json.dumps({"output_root": "configured"}), encoding="utf-8")
    explicit = (tmp_path / "explicit").resolve()
    resolved = resolve_paths(
        project_root=REPO_ROOT,
        config_path=config,
        overrides={"output_root": explicit},
    )
    assert resolved.output_root == explicit
    assert resolved.sources["output_root"] == "cli"


def test_unknown_path_field_is_rejected(tmp_path):
    """A misspelled field must fail instead of falling back silently."""
    config = tmp_path / "paths.json"
    config.write_text(json.dumps({"ouptut_root": "wrong"}), encoding="utf-8")
    with pytest.raises(PathConfigError, match="unknown"):
        resolve_paths(project_root=REPO_ROOT, config_path=config)

