from __future__ import annotations

import sys
from pathlib import Path

import pytest

import run_experiment


def test_cli_exposes_jit_as_the_fourth_arm():
    """Removing the fourth arm from the public runner would make it irreproducible."""
    assert run_experiment.ARMS == (
        "no-rail",
        "prompt-only",
        "full-rail",
        "jit-constrained",
    )


def test_all_mode_rejects_the_whole_batch_before_any_run_is_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Sequential execution would write earlier runs before detecting a later collision."""
    output_root = tmp_path / "runs"
    existing = output_root / "prompt-only" / "seed43"
    existing.mkdir(parents=True)
    marker = existing / "historical.txt"
    marker.write_text("keep\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_experiment.py", "--all", "--mode", "fixture", "--output", str(output_root)],
    )

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        run_experiment.main()

    assert marker.read_text(encoding="utf-8") == "keep\n"
    assert sorted(path.relative_to(output_root) for path in output_root.rglob("seed*")) == [
        Path("prompt-only") / "seed43"
    ]
