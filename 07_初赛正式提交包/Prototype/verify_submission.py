from __future__ import annotations

import argparse
import hashlib
import json
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
    "verify_submission.py",
)
EXTERNAL_ARTIFACTS = (
    "paper/paper.pdf",
    "AgenticReviewer/paperReview-AccessToken.txt",
)
LOCAL_SECRET_ARTIFACTS = {"AgenticReviewer/paperReview-AccessToken.txt"}
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
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip"}
EVIDENCE_LOGS = {"compile.final.log", "paper.log"}
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
        errors.append("missing required file: CHECKSUMS.sha256")
        return
    covered = set()
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        rel = rel.strip().lstrip("*")
        covered.add(rel)
        if rel in LOCAL_SECRET_ARTIFACTS:
            errors.append(f"local secret artifact must not be checksummed: {rel}")
            continue
        target = package_root / rel
        if not target.resolve().is_relative_to(package_root.resolve()):
            errors.append(f"unsafe checksum path: {rel}")
            continue
        if not target.is_file():
            errors.append(f"checksum target missing: {rel}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual.lower() != digest.lower():
            errors.append(f"checksum mismatch: {rel}")
    for path in package_root.rglob("*"):
        if path.is_file() and path != checksum_file:
            rel = path.relative_to(package_root).as_posix()
            if rel in LOCAL_SECRET_ARTIFACTS:
                continue
            if rel not in covered:
                errors.append(f"file not covered by checksums: {rel}")


def _scan_content(package_root: Path, errors: list[str]) -> None:
    for path in sorted(package_root.rglob("*")):
        relative = path.relative_to(package_root).as_posix()
        if any(part in EXCLUDED_COMPONENTS for part in path.parts) or (
            path.is_file() and path.suffix.lower() in EXCLUDED_SUFFIXES
        ):
            errors.append(f"excluded path present: {relative}")
        if "logs" in path.relative_to(package_root).parts and not relative.startswith("evidence/"):
            errors.append(f"excluded path present: {relative}")
        if path.is_file() and path.suffix.lower() == ".log":
            allowed_log = (
                relative.startswith("evidence/research_matrix_authorized/")
                and path.name in EVIDENCE_LOGS
            )
            if not allowed_log:
                errors.append(f"excluded path present: {relative}")
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        if relative in LOCAL_SECRET_ARTIFACTS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            errors.append(f"potential secret: {relative}")


def _verify_final_external_artifacts(package_root: Path, errors: list[str]) -> None:
    token = package_root / "AgenticReviewer" / "paperReview-AccessToken.txt"
    if token.is_file() and token.stat().st_size == 0:
        errors.append("empty required file: AgenticReviewer/paperReview-AccessToken.txt")

    paper = package_root / "paper" / "paper.pdf"
    if not paper.is_file():
        return
    try:
        from pypdf import PdfReader

        pages = len(PdfReader(paper).pages)
    except Exception as exc:
        errors.append(f"paper PDF is unreadable: {exc.__class__.__name__}")
        return

    try:
        manifest = json.loads((package_root / "submission_manifest.json").read_text(encoding="utf-8"))
        expected_pages = manifest["external_artifacts"]["paper/paper.pdf"]["pages"]
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        errors.append("submission manifest missing paper page count")
        return
    if not isinstance(expected_pages, int) or expected_pages < 1:
        errors.append("submission manifest has invalid paper page count")
    elif pages != expected_pages:
        errors.append(f"paper page count mismatch: expected {expected_pages}, got {pages}")


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
        if not missing_external:
            _verify_final_external_artifacts(package_root, errors)

    _scan_content(package_root, errors)
    _verify_checksums(package_root, errors)
    return {
        "stage": stage,
        "valid": not errors,
        "missing_external_artifacts": missing_external,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Prototype submission package")
    parser.add_argument("--stage", choices=("review", "final"), default="review")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = verify_package(args.root, stage=args.stage)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
