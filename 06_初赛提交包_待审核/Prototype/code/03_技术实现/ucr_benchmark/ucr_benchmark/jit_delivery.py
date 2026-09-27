"""Offline verification for a four-arm constrained-JIT comparison."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


ARMS = ("no-rail", "prompt-only", "full-rail", "jit-constrained")
SEEDS = (42, 43, 44)
BASE_FILES = (
    "config.json",
    "prompt.txt",
    "model_output.txt",
    "tool_trace.jsonl",
    "claims.json",
    "ucr_decisions.json",
    "results.json",
    "runtime_metrics.json",
    "provenance.json",
)
JIT_FILES = (
    "harness_manifest.json",
    "harness_validation.json",
    "harness/harness_archive.json",
)
ALLOWED_TOOLS = {"retrieval", "ucr", "citation_rail"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def verify_jit_comparison(root: Path) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []
    for arm in ARMS:
        for seed in SEEDS:
            relative = f"{arm}/seed{seed}"
            run_dir = root / arm / f"seed{seed}"
            required = BASE_FILES + (JIT_FILES if arm == "jit-constrained" else ())
            missing = [name for name in required if not (run_dir / name).is_file()]
            errors.extend(f"missing run artifact: {relative}/{name}" for name in missing)
            if missing:
                continue
            try:
                config = _load(run_dir / "config.json")
                results = _load(run_dir / "results.json")
                runtime = _load(run_dir / "runtime_metrics.json")
                provenance = _load(run_dir / "provenance.json")
            except (OSError, ValueError, TypeError) as exc:
                errors.append(f"unreadable run: {relative}: {exc}")
                continue
            if config.get("arm") != arm or config.get("seed") != seed:
                errors.append(f"config identity mismatch: {relative}")
            if results.get("arm") != arm or results.get("seed") != seed:
                errors.append(f"result identity mismatch: {relative}")
            if runtime.get("arm") != arm or runtime.get("seed") != seed:
                errors.append(f"runtime identity mismatch: {relative}")
            if not isinstance(runtime.get("latency_seconds"), (int, float)) or runtime["latency_seconds"] < 0:
                errors.append(f"invalid latency: {relative}")
            for name, expected in provenance.get("files", {}).items():
                path = run_dir / name
                if not path.is_file() or _sha256(path) != expected:
                    errors.append(f"provenance mismatch: {relative}/{name}")
            if arm != "jit-constrained":
                continue
            manifest = _load(run_dir / "harness_manifest.json")
            validation = _load(run_dir / "harness_validation.json")
            archive = _load(run_dir / "harness" / "harness_archive.json")
            if validation != {"valid": True, "errors": [], "fallback_reason": None}:
                errors.append(f"invalid harness validation: {relative}")
            tools = manifest.get("enabled_tools")
            if not isinstance(tools, list) or not set(tools).issubset(ALLOWED_TOOLS):
                errors.append(f"tool allowlist violation: {relative}")
            calls = runtime.get("provider_call_count")
            if not isinstance(calls, int) or calls > int(manifest.get("max_provider_calls", -1)):
                errors.append(f"provider budget violation: {relative}")
            retries = max(0, int(calls or 0) - 1)
            if retries > int(manifest.get("max_retries", -1)):
                errors.append(f"retry budget violation: {relative}")
            if config.get("rail", {}).get("enabled") is not True:
                errors.append(f"rail disabled: {relative}")
            archive_payload = {
                key: archive[key]
                for key in ("manifest", "validation", "metrics", "evidence")
                if key in archive
            }
            if archive.get("archive_sha256") != _canonical_sha256(archive_payload):
                errors.append(f"harness archive hash mismatch: {relative}")
            evidence = archive.get("evidence", [])
            expected_result_hash = _sha256(run_dir / "results.json")
            if not any(
                item.get("artifact") == "results.json"
                and item.get("sha256") == expected_result_hash
                for item in evidence
                if isinstance(item, dict)
            ):
                errors.append(f"harness evidence mismatch: {relative}")
    summary_path = root / "summary.json"
    if not summary_path.is_file():
        errors.append("missing summary.json")
    else:
        summary = _load(summary_path)
        if list(summary.get("arms", {})) != list(ARMS):
            errors.append("summary arm set mismatch")
        if not summary.get("complete") or not summary.get("all_dimensions_activated"):
            errors.append("summary incomplete")
    return errors
