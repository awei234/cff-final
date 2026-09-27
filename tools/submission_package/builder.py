from __future__ import annotations

import hashlib
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
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip"}
EVIDENCE_LOGS = {"compile.final.log", "paper.log"}


def _ignore(directory: str, names: list[str]) -> set[str]:
    in_authorized_evidence = "research_matrix_live_20260924_authorized" in Path(directory).parts
    in_demo_runs = "demo_runs" in Path(directory).parts
    ignored: set[str] = set()
    for name in names:
        suffix = Path(name).suffix.lower()
        allowed_log = in_authorized_evidence and name in EVIDENCE_LOGS
        if (
            name in EXCLUDED_NAMES
            or suffix in EXCLUDED_SUFFIXES
            or (name == "logs" and not in_demo_runs)
            or (suffix == ".log" and not allowed_log)
        ):
            ignored.add(name)
    return ignored


def _purge_excluded(package_root: Path) -> None:
    for path in sorted(package_root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if not path.exists():
            continue
        relative = path.relative_to(package_root)
        in_evidence = relative.parts and relative.parts[0] == "evidence"
        excluded = (
            any(part in EXCLUDED_NAMES for part in relative.parts)
            or ("logs" in relative.parts and not in_evidence)
            or (path.is_file() and path.suffix.lower() in EXCLUDED_SUFFIXES)
            or (path.is_file() and path.suffix.lower() == ".log" and not in_evidence)
        )
        if excluded:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def _copy_tree(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, ignore=_ignore, dirs_exist_ok=True)


def build_review_package(source_work: Path, package_root: Path) -> dict[str, object]:
    """Assemble an allowlisted review package from a JiuwenSwarm work copy."""
    source_work = source_work.resolve()
    package_root.mkdir(parents=True, exist_ok=True)
    _purge_excluded(package_root)
    (package_root / "paper").mkdir(exist_ok=True)
    (package_root / "AgenticReviewer").mkdir(exist_ok=True)

    _copy_tree(source_work / "code", package_root / "code")
    for name in ("architecture.md", "module_call.md", "innovation.md"):
        source = source_work / "docs" / name
        if source.is_file():
            destination = package_root / "docs" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
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
    shutil.copy2(Path(__file__).with_name("verifier.py"), package_root / "verify_submission.py")
    return {
        "source": str(source_work),
        "destination": str(package_root.resolve()),
        "canonical_jit": CANONICAL_JIT,
        "evidence": copied_evidence,
    }


def write_checksums(package_root: Path) -> Path:
    """Write stable SHA-256 entries for every package file except the list itself."""
    package_root = package_root.resolve()
    checksum_file = package_root / "CHECKSUMS.sha256"
    lines: list[str] = []
    for path in sorted(item for item in package_root.rglob("*") if item.is_file()):
        if path == checksum_file:
            continue
        relative = path.relative_to(package_root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {relative}")
    checksum_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_file
