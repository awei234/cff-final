from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from tools.submission_package.builder import build_review_package, write_checksums
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
    write(work / "demo_runs" / "research_matrix_live_20260924_authorized" / "context-engineering" / "compile.final.log")
    write(work / "demo_runs" / "research_matrix_live_20260924_authorized" / "context-engineering" / "paper.log")
    write(work / "demo_runs" / "research_matrix_live_20260924_authorized" / "context-engineering" / "logs" / "full-rail-stdout.txt")
    write(work / "demo_runs" / "research_matrix_live_20260925_seed43" / "report.json")
    write(work / "demo_runs" / "research_matrix_live_20260925_seed44" / "report.json")
    write(work / "demo_runs" / "jit_comparison_v2_final" / "summary.json", '{"complete": true}')
    write(work / "demo_runs" / "jit_smoke_seed42" / "discard.json")
    write(work / "harness_packages" / "jit-constrained-research-harness" / "manifest.json")
    write(work / "harness_packages" / "dist" / "harness.zip")
    write(work / "runtime_local" / "config.yaml", "api_key: should-not-copy")
    write(work / "code" / "03_技术实现" / "jiuwenswarm" / "backend-bootstrap.err.log")
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
    write_checksums(package)


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
    assert not (package / "code/03_技术实现/jiuwenswarm/backend-bootstrap.err.log").exists()
    assert (package / "evidence/research_matrix_authorized/context-engineering/compile.final.log").is_file()
    assert (package / "evidence/research_matrix_authorized/context-engineering/paper.log").is_file()
    assert (package / "evidence/research_matrix_authorized/context-engineering/logs/full-rail-stdout.txt").is_file()
    assert not (package / "evidence/jit_smoke_seed42").exists()
    assert not list(package.rglob("*.zip"))
    assert (package / "verify_submission.py").is_file()
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
    write(package / "code" / "backend.log", "runtime output")
    write(package / "code" / "credentials.txt", "api_key=sk-live-abcdefghijklmnopqrstuvwxyz123456")

    result = verify_package(package, stage="review")

    assert result["valid"] is False
    assert any("excluded path" in error for error in result["errors"])
    assert any("code/backend.log" in error for error in result["errors"])
    assert any("potential secret" in error for error in result["errors"])


def test_checksum_verification_detects_tampering(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    package = tmp_path / "Prototype"
    build_review_package(source, package)
    add_required_documents(package)
    target = package / "README.md"
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    write_checksums(package)

    assert verify_package(package, stage="review")["valid"] is True

    target.write_text("tampered", encoding="utf-8")
    result = verify_package(package, stage="review")

    assert result["valid"] is False
    assert "checksum mismatch: README.md" in result["errors"]


def test_generated_checksums_exclude_the_checksum_file_itself(tmp_path: Path) -> None:
    package = tmp_path / "Prototype"
    write(package / "README.md", "review")

    checksum_file = write_checksums(package)

    text = checksum_file.read_text(encoding="utf-8")
    assert "README.md" in text
    assert "CHECKSUMS.sha256" not in text


def test_rebuild_does_not_overwrite_curated_submission_documents(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    package = tmp_path / "Prototype"
    build_review_package(source, package)
    architecture = package / "docs" / "architecture.md"
    architecture.write_text("curated submission architecture", encoding="utf-8")
    write(package / "code" / "logs" / "stale.txt")
    write(package / "code" / "stale.log")

    build_review_package(source, package)

    assert architecture.read_text(encoding="utf-8") == "curated submission architecture"
    assert not (package / "code" / "logs").exists()
    assert not (package / "code" / "stale.log").exists()


def test_packaged_verifier_runs_standalone(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    package = tmp_path / "Prototype"
    build_review_package(source, package)
    add_required_documents(package)

    completed = subprocess.run(
        [sys.executable, str(package / "verify_submission.py"), "--stage", "review"],
        cwd=package,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["valid"] is True
