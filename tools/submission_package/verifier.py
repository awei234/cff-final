from __future__ import annotations

import hashlib
import re
from pathlib import Path


REQUIRED_DIRECTORIES = ("paper", "AgenticReviewer", "code", "docs", "evidence")
REQUIRED_DOCUMENTS = (
    "docs/architecture.md",
    "docs/module_call.md",
    "docs/innovation.md",
    "framework_contribution.md",
    "resource_report.md",
    "提交说明.md",
    "README.md",
    "submission_manifest.json",
    "SOURCE_STATE.md",
)
EXTERNAL_ARTIFACTS = (
    "paper/paper.pdf",
    "AgenticReviewer/paperReview-AccessToken.txt",
)
REQUIRED_EVIDENCE = (
    "evidence/research_matrix_authorized",
    "evidence/context_engineering_seed43",
    "evidence/context_engineering_seed44",
    "evidence/jit_comparison_v2_final",
)
EXCLUDED_COMPONENTS = {
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".pytest_tmp",
    "runtime_local",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".zip"}
SECRET_PATTERNS = (
    re.compile(r"sk-(?!(?:test|demo|example))[-A-Za-z0-9_]{20,}", re.IGNORECASE),
    re.compile(r"authorization\s*:\s*bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE),
    re.compile(
        r"(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9_-]{24,}",
        re.IGNORECASE,
    ),
)


def _verify_checksums(package_root: Path, errors: list[str]) -> None:
    checksum_file = package_root / "CHECKSUMS.sha256"
    if not checksum_file.is_file():
        return
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        rel = rel.strip().lstrip("*")
        target = package_root / rel
        if not target.is_file():
            errors.append(f"checksum target missing: {rel}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual.lower() != digest.lower():
            errors.append(f"checksum mismatch: {rel}")


def _scan_content(package_root: Path, errors: list[str]) -> None:
    for path in sorted(package_root.rglob("*")):
        relative = path.relative_to(package_root).as_posix()
        if any(part in EXCLUDED_COMPONENTS for part in path.parts) or (
            path.is_file() and path.suffix.lower() in EXCLUDED_SUFFIXES
        ):
            errors.append(f"excluded path present: {relative}")
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            errors.append(f"potential secret: {relative}")


def verify_package(package_root: Path, stage: str = "review") -> dict[str, object]:
    if stage not in {"review", "final"}:
        raise ValueError("stage must be 'review' or 'final'")
    package_root = package_root.resolve()
    errors: list[str] = []
    for rel in REQUIRED_DIRECTORIES:
        if not (package_root / rel).is_dir():
            errors.append(f"missing required directory: {rel}")
    for rel in REQUIRED_DOCUMENTS:
        if not (package_root / rel).is_file():
            errors.append(f"missing required file: {rel}")
    for rel in REQUIRED_EVIDENCE:
        if not (package_root / rel).is_dir():
            errors.append(f"missing required evidence: {rel}")

    missing_external = [rel for rel in EXTERNAL_ARTIFACTS if not (package_root / rel).is_file()]
    if stage == "final":
        errors.extend(f"missing required file: {rel}" for rel in missing_external)

    _scan_content(package_root, errors)
    _verify_checksums(package_root, errors)
    return {
        "stage": stage,
        "valid": not errors,
        "missing_external_artifacts": missing_external,
        "errors": errors,
    }
