"""Read-only verification reports for formal generation runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .artifact_contract import (
    HASHED_ARTIFACTS,
    REQUIRED_ARTIFACTS,
    ContractIssue,
    load_json_object,
    load_jsonl,
    sha256_file,
)


REQUIRED_JSON_FIELDS = {
    "run_manifest.json": {
        "schema_version",
        "run_id",
        "topic",
        "provider",
        "model",
        "seed",
        "mode",
        "created_at_utc",
        "status",
        "required_artifacts",
    },
    "results.json": {"schema_version", "run_id", "status", "claims", "measurements"},
    "resource.json": {
        "schema_version",
        "run_id",
        "token_usage",
        "duration_seconds",
        "cost",
        "measurement_status",
    },
    "provenance.json": {
        "schema_version",
        "run_id",
        "source_commit",
        "source_commit_status",
        "generator",
        "artifact_hashes",
    },
    "verification_report.json": {
        "schema_version",
        "run_id",
        "valid",
        "checks",
        "errors",
        "verified_at_utc",
        "run_manifest_sha256",
        "provenance_sha256",
    },
}

TRACE_FIELDS = {"event_id", "operation_id", "tool", "status", "timestamp_utc", "evidence"}


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    run_id: str | None
    checks: tuple[dict[str, object], ...]
    errors: tuple[ContractIssue, ...]
    verified_at_utc: str
    run_manifest_sha256: str | None
    provenance_sha256: str | None

    def as_report(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "valid": self.valid,
            "checks": list(self.checks),
            "errors": [
                {"code": issue.code, "artifact": issue.artifact, "message": issue.message}
                for issue in self.errors
            ],
            "verified_at_utc": self.verified_at_utc,
            "run_manifest_sha256": self.run_manifest_sha256,
            "provenance_sha256": self.provenance_sha256,
        }


def verify_run(run_dir: Path, *, require_stored_report: bool = True) -> VerificationResult:
    """Recompute the complete generation contract without writing the run."""
    issues: list[ContractIssue] = []
    checks: list[dict[str, object]] = []

    def record(name: str, passed: bool, artifact: str, code: str, message: str) -> None:
        checks.append({"name": name, "artifact": artifact, "passed": passed})
        if not passed:
            issues.append(ContractIssue(code, artifact, message))

    documents: dict[str, dict[str, object] | None] = {}
    json_names = ["run_manifest.json", "results.json", "resource.json", "provenance.json"]
    if require_stored_report:
        json_names.append("verification_report.json")
    for name in json_names:
        document, document_issues = load_json_object(run_dir / name)
        documents[name] = document
        issues.extend(document_issues)

    for name in REQUIRED_ARTIFACTS:
        if name == "verification_report.json" and not require_stored_report:
            continue
        record(
            f"exists:{name}",
            (run_dir / name).is_file(),
            name,
            "artifact_missing",
            "required artifact is missing",
        )

    if run_dir.is_dir():
        for path in sorted((item for item in run_dir.iterdir() if item.is_file()), key=lambda item: item.name):
            if path.name not in REQUIRED_ARTIFACTS:
                record(
                    f"unknown:{path.name}",
                    False,
                    path.name,
                    "artifact_unknown",
                    "file is not part of the frozen generation artifact contract",
                )

    for name, required_fields in REQUIRED_JSON_FIELDS.items():
        if name == "verification_report.json" and not require_stored_report:
            continue
        document = documents.get(name)
        if document is None:
            continue
        missing_fields = sorted(required_fields - set(document))
        record(
            f"fields:{name}",
            not missing_fields,
            name,
            "artifact_invalid",
            f"missing required fields: {', '.join(missing_fields)}",
        )

    manifest = documents.get("run_manifest.json")
    provenance = documents.get("provenance.json")
    report = documents.get("verification_report.json")
    manifest_hash = sha256_file(run_dir / "run_manifest.json") if manifest is not None else None
    provenance_hash = sha256_file(run_dir / "provenance.json") if provenance is not None else None
    run_id = manifest.get("run_id") if manifest is not None else None
    if not isinstance(run_id, str):
        run_id = None

    if manifest is not None:
        record(
            "manifest:required_artifacts",
            manifest.get("required_artifacts") == list(REQUIRED_ARTIFACTS),
            "run_manifest.json",
            "artifact_invalid",
            "required_artifacts does not match the fixed contract",
        )
        record(
            "manifest:completed",
            manifest.get("status") == "completed",
            "run_manifest.json",
            "artifact_invalid",
            "manifest status is not completed",
        )

    for name in ("results.json", "resource.json", "provenance.json"):
        document = documents.get(name)
        if document is not None and run_id is not None:
            record(
                f"run_id:{name}",
                document.get("run_id") == run_id,
                name,
                "run_identity_mismatch",
                "artifact run_id differs from the manifest",
            )
    if require_stored_report and report is not None and run_id is not None:
        record(
            "run_id:verification_report.json",
            report.get("run_id") == run_id,
            "verification_report.json",
            "run_identity_mismatch",
            "artifact run_id differs from the manifest",
        )

    trace_records, trace_issues = load_jsonl(run_dir / "tool_trace.jsonl")
    issues.extend(trace_issues)
    for index, event in enumerate(trace_records, start=1):
        missing = sorted(TRACE_FIELDS - set(event))
        record(
            f"trace:event-{index}",
            not missing,
            "tool_trace.jsonl",
            "artifact_invalid",
            f"trace event {index} missing fields: {', '.join(missing)}",
        )

    for name in ("prompt.txt", "paper.tex"):
        path = run_dir / name
        if path.is_file():
            try:
                non_empty = bool(path.read_text(encoding="utf-8").strip())
            except (OSError, UnicodeDecodeError):
                non_empty = False
            record(f"content:{name}", non_empty, name, "artifact_invalid", "text artifact is empty or unreadable")

    pdf_path = run_dir / "paper.pdf"
    if pdf_path.is_file():
        try:
            pdf = pdf_path.read_bytes()
        except OSError:
            pdf = b""
        record(
            "content:paper.pdf",
            pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF"),
            "paper.pdf",
            "pdf_invalid",
            "PDF header or EOF marker is invalid",
        )

    resource = documents.get("resource.json")
    if resource is not None and manifest is not None and manifest.get("mode") == "fixture":
        fixture_measurements_valid = (
            resource.get("measurement_status") == "not_applicable"
            and resource.get("token_usage") is None
            and resource.get("duration_seconds") is None
            and resource.get("cost") is None
        )
        record(
            "resource:fixture_measurements",
            fixture_measurements_valid,
            "resource.json",
            "artifact_invalid",
            "fixture measurements must be null and not_applicable",
        )

    if provenance is not None:
        expected_hashes = provenance.get("artifact_hashes")
        hashes_are_object = isinstance(expected_hashes, dict)
        record(
            "provenance:artifact_hashes",
            hashes_are_object and set(expected_hashes) == set(HASHED_ARTIFACTS),
            "provenance.json",
            "artifact_invalid",
            "artifact_hashes must contain exactly the protected artifacts",
        )
        if hashes_are_object:
            for name in HASHED_ARTIFACTS:
                path = run_dir / name
                if not path.is_file():
                    continue
                actual = sha256_file(path)
                record(
                    f"hash:{name}",
                    expected_hashes.get(name) == actual,
                    name,
                    "hash_mismatch",
                    "artifact SHA-256 differs from provenance",
                )

    if require_stored_report and report is not None:
        stored_fresh = (
            report.get("run_manifest_sha256") == manifest_hash
            and report.get("provenance_sha256") == provenance_hash
            and report.get("valid") is True
        )
        record(
            "verification_report:fresh",
            stored_fresh,
            "verification_report.json",
            "verification_report_stale",
            "stored verification report does not match current identity hashes",
        )

    errors = tuple(issues)
    return VerificationResult(
        valid=not errors,
        run_id=run_id,
        checks=tuple(checks),
        errors=errors,
        verified_at_utc=datetime.now(timezone.utc).isoformat(),
        run_manifest_sha256=manifest_hash,
        provenance_sha256=provenance_hash,
    )
