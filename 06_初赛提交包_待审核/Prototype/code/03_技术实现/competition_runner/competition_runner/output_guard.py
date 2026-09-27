"""Exclusive output-directory reservation for formal runs."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Sequence


RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class OutputGuardError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _validate_run_id(run_id: str) -> None:
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise OutputGuardError("run_id_invalid", f"run id is not a safe path segment: {run_id!r}")


def _ensure_output_root(output_root: Path) -> None:
    try:
        output_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OutputGuardError("output_root_invalid", f"output root is not a usable directory: {output_root}") from exc


def reserve_output_directory(output_root: Path, run_id: str) -> Path:
    """Create and return one previously nonexistent run directory."""
    _validate_run_id(run_id)
    _ensure_output_root(output_root)
    target = output_root / run_id
    try:
        target.mkdir()
    except FileExistsError as exc:
        raise OutputGuardError("output_exists", f"output directory already exists: {target}") from exc
    return target


def reserve_output_directories(output_root: Path, run_ids: Sequence[str]) -> tuple[Path, ...]:
    """Reserve a batch without leaving partially reserved run directories."""
    for run_id in run_ids:
        _validate_run_id(run_id)
    _ensure_output_root(output_root)
    targets = tuple(output_root / run_id for run_id in run_ids)
    for target in targets:
        if target.exists():
            raise OutputGuardError("output_exists", f"output directory already exists: {target}")
    created: list[Path] = []
    try:
        for target in targets:
            target.mkdir()
            created.append(target)
    except FileExistsError as exc:
        for target in reversed(created):
            target.rmdir()
        raise OutputGuardError("output_exists", f"output directory already exists: {target}") from exc
    return targets
