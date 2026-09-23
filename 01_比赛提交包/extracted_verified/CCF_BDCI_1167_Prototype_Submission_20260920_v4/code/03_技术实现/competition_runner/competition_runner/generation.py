"""Non-overwriting generation orchestration with an offline fixture backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Protocol

from .artifact_contract import HASHED_ARTIFACTS, REQUIRED_ARTIFACTS, sha256_file
from .output_guard import reserve_output_directory
from .verification import verify_run


class GenerationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class GenerationRequest:
    topic: str
    provider: str
    model: str
    seed: int
    mode: str
    output: Path
    source_commit: str | None


@dataclass(frozen=True)
class GeneratedContent:
    prompt: str
    tool_events: tuple[dict[str, object], ...]
    results: dict[str, object]
    paper_tex: str
    paper_pdf: bytes
    resource: dict[str, object]


class GenerationBackend(Protocol):
    def generate(self, request: GenerationRequest, run_id: str) -> GeneratedContent: ...


class FixtureBackend:
    """Create deterministic, explicitly non-live evidence for contract tests."""

    def generate(self, request: GenerationRequest, run_id: str) -> GeneratedContent:
        timestamp = datetime.now(timezone.utc).isoformat()
        return GeneratedContent(
            prompt=f"[FIXTURE ONLY]\nTopic: {request.topic}\nSeed: {request.seed}\n",
            tool_events=(
                {
                    "event_id": "event-1",
                    "operation_id": "operation-1",
                    "tool": "fixture_generator",
                    "status": "success",
                    "timestamp_utc": timestamp,
                    "evidence": {"mode": "fixture", "network_used": False},
                },
            ),
            results={
                "schema_version": "1.0",
                "run_id": run_id,
                "status": "fixture_completed",
                "claims": [],
                "measurements": [],
            },
            paper_tex=(
                "% FIXTURE ONLY - NOT EXPERIMENTAL EVIDENCE\n"
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                f"Fixture for {request.topic}.\n"
                "\\end{document}\n"
            ),
            paper_pdf=b"%PDF-1.4\n% fixture only - not experimental evidence\n%%EOF\n",
            resource={
                "schema_version": "1.0",
                "run_id": run_id,
                "token_usage": None,
                "duration_seconds": None,
                "cost": None,
                "measurement_status": "not_applicable",
            },
        )


def _write_bytes_atomic(path: Path, contents: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(contents)
    temporary.replace(path)


def _write_text_atomic(path: Path, contents: str) -> None:
    _write_bytes_atomic(path, contents.encode("utf-8"))


def _write_json_atomic(path: Path, value: dict[str, object]) -> None:
    _write_text_atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _make_run_id(request: GenerationRequest, created_at: datetime) -> str:
    topic_digest = hashlib.sha256(request.topic.encode("utf-8")).hexdigest()[:12]
    timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    return f"{request.provider}-{request.seed}-{topic_digest}-{timestamp}"


def generate_run(
    request: GenerationRequest,
    backend: GenerationBackend | None = None,
) -> dict[str, object]:
    """Generate one immutable run directory and return its verification report."""
    if not request.topic.strip():
        raise GenerationError("topic_invalid", "topic must not be empty")
    if request.mode not in {"fixture", "live"}:
        raise GenerationError("mode_invalid", f"unsupported generation mode: {request.mode}")
    output = reserve_output_directory(request.output.parent, request.output.name)
    created_at = datetime.now(timezone.utc)
    run_id = _make_run_id(request, created_at)
    manifest: dict[str, object] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "topic": request.topic,
        "provider": request.provider,
        "model": request.model,
        "seed": request.seed,
        "mode": request.mode,
        "created_at_utc": created_at.isoformat(),
        "status": "running",
        "required_artifacts": list(REQUIRED_ARTIFACTS),
    }
    _write_json_atomic(output / "run_manifest.json", manifest)
    try:
        if backend is None or (request.mode == "live" and isinstance(backend, FixtureBackend)):
            raise GenerationError(
                "generation_backend_unavailable",
                "no live generation backend is configured",
            )
        content = backend.generate(request, run_id)
        _write_text_atomic(output / "prompt.txt", content.prompt)
        trace = "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in content.tool_events)
        _write_text_atomic(output / "tool_trace.jsonl", trace)
        _write_json_atomic(output / "results.json", content.results)
        _write_text_atomic(output / "paper.tex", content.paper_tex)
        _write_bytes_atomic(output / "paper.pdf", content.paper_pdf)
        _write_json_atomic(output / "resource.json", content.resource)
        provenance = {
            "schema_version": "1.0",
            "run_id": run_id,
            "source_commit": request.source_commit,
            "source_commit_status": "available" if request.source_commit else "unavailable",
            "generator": {"name": type(backend).__name__, "mode": request.mode},
            "artifact_hashes": {name: sha256_file(output / name) for name in HASHED_ARTIFACTS},
        }
        _write_json_atomic(output / "provenance.json", provenance)
        manifest["status"] = "completed"
        _write_json_atomic(output / "run_manifest.json", manifest)
        initial = verify_run(output, require_stored_report=False)
        if not initial.valid:
            raise GenerationError("artifact_invalid", "generated artifacts failed initial verification")
        _write_json_atomic(output / "verification_report.json", initial.as_report())
        final = verify_run(output)
        if not final.valid:
            raise GenerationError("artifact_invalid", "stored verification report failed revalidation")
        return final.as_report()
    except GenerationError as exc:
        manifest["status"] = "failed"
        manifest["failure_code"] = exc.code
        _write_json_atomic(output / "run_manifest.json", manifest)
        raise
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["failure_code"] = "generation_failed"
        _write_json_atomic(output / "run_manifest.json", manifest)
        raise GenerationError("generation_failed", f"generation failed: {exc}") from exc
