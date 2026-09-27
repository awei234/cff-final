from __future__ import annotations

import shutil
from pathlib import Path


CANONICAL_JIT = "jit_comparison_v2_final"
EVIDENCE_MAPPINGS = (
    ("research_matrix_live_20260924_authorized", "research_matrix_authorized"),
    ("research_matrix_live_20260925_seed43", "context_engineering_seed43"),
    ("research_matrix_live_20260925_seed44", "context_engineering_seed44"),
    (CANONICAL_JIT, CANONICAL_JIT),
)
EXCLUDED_NAMES = {
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".pytest_tmp",
    ".git",
    "runtime_local",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".zip"}


def _ignore(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in EXCLUDED_NAMES or Path(name).suffix.lower() in EXCLUDED_SUFFIXES
    }


def _copy_tree(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, ignore=_ignore, dirs_exist_ok=True)


def build_review_package(source_work: Path, package_root: Path) -> dict[str, object]:
    """Assemble an allowlisted review package from a JiuwenSwarm work copy."""
    source_work = source_work.resolve()
    package_root.mkdir(parents=True, exist_ok=True)
    (package_root / "paper").mkdir(exist_ok=True)
    (package_root / "AgenticReviewer").mkdir(exist_ok=True)

    _copy_tree(source_work / "code", package_root / "code")
    for name in ("architecture.md", "module_call.md", "innovation.md"):
        source = source_work / "docs" / name
        if source.is_file():
            destination = package_root / "docs" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    reports = source_work / "docs" / "reports"
    _copy_tree(reports, package_root / "docs" / "reports")

    copied_evidence: list[str] = []
    for source_name, destination_name in EVIDENCE_MAPPINGS:
        source = source_work / "demo_runs" / source_name
        if source.is_dir():
            _copy_tree(source, package_root / "evidence" / destination_name)
            copied_evidence.append(destination_name)

    _copy_tree(source_work / "harness_packages", package_root / "harness_packages")
    return {
        "source": str(source_work),
        "destination": str(package_root.resolve()),
        "canonical_jit": CANONICAL_JIT,
        "evidence": copied_evidence,
    }
