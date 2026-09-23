"""Shared file-level primitives for formal generation artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


REQUIRED_ARTIFACTS = (
    "run_manifest.json",
    "prompt.txt",
    "tool_trace.jsonl",
    "results.json",
    "paper.tex",
    "paper.pdf",
    "resource.json",
    "verification_report.json",
    "provenance.json",
)

HASHED_ARTIFACTS = (
    "prompt.txt",
    "tool_trace.jsonl",
    "results.json",
    "paper.tex",
    "paper.pdf",
    "resource.json",
)


@dataclass(frozen=True)
class ContractIssue:
    code: str
    artifact: str
    message: str


def sha256_file(path: Path) -> str:
    """Return the uppercase SHA-256 digest of the exact file bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json_object(path: Path) -> tuple[dict[str, object] | None, tuple[ContractIssue, ...]]:
    """Read one JSON object while preserving a stable artifact error contract."""
    if not path.is_file():
        return None, (ContractIssue("artifact_missing", path.name, "required artifact is missing"),)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, (ContractIssue("artifact_invalid", path.name, f"invalid JSON object: {exc}"),)
    if not isinstance(value, dict):
        return None, (ContractIssue("artifact_invalid", path.name, "JSON artifact must be an object"),)
    return value, ()


def load_jsonl(path: Path) -> tuple[tuple[dict[str, object], ...], tuple[ContractIssue, ...]]:
    """Read non-empty JSONL object records with line-specific failures."""
    if not path.is_file():
        return (), (ContractIssue("artifact_missing", path.name, "required artifact is missing"),)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        records: list[dict[str, object]] = []
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                raise ValueError(f"line {line_number} is empty")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number} is not an object")
            records.append(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return (), (ContractIssue("artifact_invalid_jsonl", path.name, f"invalid JSONL: {exc}"),)
    if not records:
        return (), (ContractIssue("artifact_invalid_jsonl", path.name, "JSONL artifact is empty"),)
    return tuple(records), ()
