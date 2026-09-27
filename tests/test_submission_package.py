from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.submission_package.builder import build_review_package
from tools.submission_package.verifier import verify_package


def write(path: Path, content: str = "ok") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_source(root: Path) -> Path:
    work = root / "work"
    write(work / "code" / "03_技术实现" / "ucr_benchmark" / "runner.py")
    write(work / "code" / "03_技术实现" / "jiuwenswarm" / "frontend" / "dist" / "index.html")
    write(work / "code" / "03_技术实现" / "jiuwenswarm" / ".venv" / "secret.py")
    write(work / "code" / "03_技术实现" / "jiuwenswarm" / "node_modules" / "pkg.js")
    write(work / "docs" / "architecture.md")
    write(work / "docs" / "module_call.md")
    write(work / "docs" / "innovation.md")
    write(work / "demo_runs" / "research_matrix_live_20260924_authorized" / "review.json", '{"allow_paper": true}')
    write(work / "demo_runs" / "research_matrix_live_20260925_seed43" / "report.json")
    write(work / "demo_runs" / "research_matrix_live_20260925_seed44" / "report.json")
    write(work / "demo_runs" / "jit_comparison_v2_final" / "summary.json", '{"complete": true}')
    write(work / "demo_runs" / "jit_smoke_seed42" / "discard.json")
    write(work / "harness_packages" / "jit-constrained-research-harness" / "manifest.json")
    write(work / "harness_packages" / "dist" / "harness.zip")
    write(work / "runtime_local" / "config.yaml", "api_key: should-not-copy")
    return work


def add_required_documents(package: Path) -> None:
    for rel in (
        "docs/architecture.md",
        "docs/module_call.md",
        "docs/innovation.md",
        "framework_contribution.md",
        "resource_report.md",
        "提交说明.md",
        "README.md",
        "SOURCE_STATE.md",
    ):
        write(package / rel)
    write(
        package / "submission_manifest.json",
        json.dumps({"package_status": "review_ready_missing_external_artifacts"}),
    )


def test_builder_uses_allowlist_and_creates_external_artifact_directories(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    package = tmp_path / "Prototype"

    report = build_review_package(source, package)

    assert (package / "paper").is_dir()
    assert (package / "AgenticReviewer").is_dir()
    assert (package / "code/03_技术实现/ucr_benchmark/runner.py").is_file()
    assert (package / "code/03_技术实现/jiuwenswarm/frontend/dist/index.html").is_file()
    assert not (package / "code/03_技术实现/jiuwenswarm/.venv").exists()
    assert not (package / "code/03_技术实现/jiuwenswarm/node_modules").exists()
    assert not (package / "runtime_local").exists()
    assert not (package / "evidence/jit_smoke_seed42").exists()
    assert not list(package.rglob("*.zip"))
    assert report["canonical_jit"] == "jit_comparison_v2_final"


def test_review_stage_allows_only_two_external_artifacts_to_be_missing(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    package = tmp_path / "Prototype"
    build_review_package(source, package)
    add_required_documents(package)

    result = verify_package(package, stage="review")

    assert result["valid"] is True
    assert result["missing_external_artifacts"] == [
        "paper/paper.pdf",
        "AgenticReviewer/paperReview-AccessToken.txt",
    ]
    assert result["errors"] == []


def test_final_stage_requires_paper_and_access_token(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    package = tmp_path / "Prototype"
    build_review_package(source, package)
    add_required_documents(package)

    result = verify_package(package, stage="final")

    assert result["valid"] is False
    assert result["errors"] == [
        "missing required file: paper/paper.pdf",
        "missing required file: AgenticReviewer/paperReview-AccessToken.txt",
    ]


def test_verifier_rejects_excluded_content_and_secret_values(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    package = tmp_path / "Prototype"
    build_review_package(source, package)
    add_required_documents(package)
    write(package / "code" / "__pycache__" / "bad.pyc")
    write(package / "code" / "credentials.txt", "api_key=sk-live-abcdefghijklmnopqrstuvwxyz123456")

    result = verify_package(package, stage="review")

    assert result["valid"] is False
    assert any("excluded path" in error for error in result["errors"])
    assert any("potential secret" in error for error in result["errors"])


def test_checksum_verification_detects_tampering(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    package = tmp_path / "Prototype"
    build_review_package(source, package)
    add_required_documents(package)
    target = package / "README.md"
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    write(package / "CHECKSUMS.sha256", f"{digest}  README.md\n")

    assert verify_package(package, stage="review")["valid"] is True

    target.write_text("tampered", encoding="utf-8")
    result = verify_package(package, stage="review")

    assert result["valid"] is False
    assert "checksum mismatch: README.md" in result["errors"]
