from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_reserve_output_directory_creates_one_new_directory(tmp_path: Path):
    """Removing exclusive creation must make a fresh formal run impossible to reserve."""
    output_guard = importlib.import_module("competition_runner.output_guard")
    output_root = tmp_path / "runs"

    reserved = output_guard.reserve_output_directory(output_root, "run-001")

    assert reserved == output_root / "run-001"
    assert reserved.is_dir()


def test_reserve_output_directory_refuses_an_existing_empty_directory(tmp_path: Path):
    """Replacing the exclusive mkdir with exist_ok=True must expose this regression."""
    output_guard = importlib.import_module("competition_runner.output_guard")
    target = tmp_path / "runs" / "run-001"
    target.mkdir(parents=True)

    with pytest.raises(output_guard.OutputGuardError) as exc:
        output_guard.reserve_output_directory(tmp_path / "runs", "run-001")

    assert exc.value.code == "output_exists"
    assert list(target.iterdir()) == []


@pytest.mark.parametrize("run_id", ["", ".", "..", "nested/run", r"nested\run", "bad:name"])
def test_reserve_output_directory_rejects_an_unsafe_run_id(tmp_path: Path, run_id: str):
    """Removing the one-segment allowlist must permit path escape or platform-specific names."""
    output_guard = importlib.import_module("competition_runner.output_guard")
    output_root = tmp_path / "runs"

    with pytest.raises(output_guard.OutputGuardError) as exc:
        output_guard.reserve_output_directory(output_root, run_id)

    assert exc.value.code == "run_id_invalid"
    assert not output_root.exists()


def test_reserve_output_directory_rejects_a_file_as_output_root(tmp_path: Path):
    """Leaking pathlib errors here would remove the stable output_root_invalid contract."""
    output_guard = importlib.import_module("competition_runner.output_guard")
    output_root = tmp_path / "runs"
    output_root.write_text("historical\n", encoding="utf-8")

    with pytest.raises(output_guard.OutputGuardError) as exc:
        output_guard.reserve_output_directory(output_root, "run-001")

    assert exc.value.code == "output_root_invalid"
    assert output_root.read_text(encoding="utf-8") == "historical\n"


def test_reserve_output_directories_rejects_the_whole_batch_before_writing(tmp_path: Path):
    """Sequential reservation would leave a partial batch before detecting a later collision."""
    output_guard = importlib.import_module("competition_runner.output_guard")
    output_root = tmp_path / "runs"
    existing = output_root / "run-b"
    existing.mkdir(parents=True)
    marker = existing / "historical.txt"
    marker.write_text("keep\n", encoding="utf-8")

    with pytest.raises(output_guard.OutputGuardError) as exc:
        output_guard.reserve_output_directories(output_root, ["run-a", "run-b", "run-c"])

    assert exc.value.code == "output_exists"
    assert not (output_root / "run-a").exists()
    assert marker.read_text(encoding="utf-8") == "keep\n"
    assert not (output_root / "run-c").exists()
