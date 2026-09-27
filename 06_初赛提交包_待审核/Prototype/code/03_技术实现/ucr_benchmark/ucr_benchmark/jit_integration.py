"""Bridge the UCR runner to the constrained Harness implementation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _competition_runner_root() -> Path:
    return Path(__file__).resolve().parents[2] / "competition_runner"


def _load_harness_api():
    root = _competition_runner_root()
    if not (root / "competition_runner" / "harness" / "planner.py").is_file():
        raise RuntimeError(f"competition_runner Harness implementation not found: {root}")
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    from competition_runner.harness.archive import archive_run
    from competition_runner.harness.planner import build_harness_manifest
    from competition_runner.harness.validator import validate_manifest

    return build_harness_manifest, validate_manifest, archive_run


def prepare_jit_policy() -> tuple[dict[str, Any], dict[str, Any]]:
    build_harness_manifest, validate_manifest, _ = _load_harness_api()
    manifest = dict(
        build_harness_manifest(
            {
                "experiment_required": True,
                "requires_evidence": True,
                "repair_required": False,
                "cost_limited": False,
            }
        )
    )
    result = validate_manifest(manifest)
    validation = {
        "valid": result.valid,
        "errors": list(result.errors),
        "fallback_reason": result.fallback_reason,
    }
    return dict(result.manifest), validation


def archive_jit_policy(
    output_dir: Path,
    *,
    manifest: dict[str, Any],
    validation: dict[str, Any],
    metrics: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> Path:
    _, _, archive_run = _load_harness_api()
    return archive_run(
        output_dir,
        manifest=manifest,
        validation=validation,
        metrics=metrics,
        evidence=evidence,
    )
