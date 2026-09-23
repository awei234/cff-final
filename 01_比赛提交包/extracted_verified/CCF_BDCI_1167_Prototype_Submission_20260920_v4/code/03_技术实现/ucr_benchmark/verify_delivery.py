#!/usr/bin/env python3
"""Offline integrity checks for the UCR-activated project delivery."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ARMS = ("no-rail", "prompt-only", "full-rail")
SEEDS = (42, 43, 44)
RUN_FILES = (
    "config.json",
    "prompt.txt",
    "model_output.txt",
    "tool_trace.jsonl",
    "claims.json",
    "ucr_decisions.json",
    "results.json",
    "provenance.json",
)
HASHED_FILES = ("config.json", "prompt.txt", "model_output.txt", "tool_trace.jsonl")
ROOT_CREDENTIAL_FILES = (
    "run_v7_experiments.sh",
    "run_v7_qwen.sh",
    "test_zhipu.py",
    "test_qwen.py",
    "test_qwen2.py",
    "test_qwen_models.py",
    ".zcode/tools/fix_env_tokens.sh",
)
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9._-]{16,}"),
    re.compile(r"[0-9a-fA-F]{16,}\.[A-Za-z0-9._-]{16,}"),
    re.compile(r"JUP[A-Za-z0-9]{16,}"),
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_project(project_root: Path) -> list[str]:
    project_root = Path(project_root).resolve()
    benchmark = project_root / "03_技术实现" / "ucr_benchmark"
    after = benchmark / "results" / "after"
    errors: list[str] = []

    required_project_files = (
        project_root / "README_UCR.md",
        project_root / "SECURITY.md",
        benchmark / "README.md",
        benchmark / "config" / "experiment.json",
        benchmark / "config" / "scenarios.json",
        after / "summary.json",
        benchmark / "results" / "comparison.json",
    )
    for path in required_project_files:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(project_root)}")

    measured_runs = 0
    unexecuted_total = 0
    for arm in ARMS:
        for seed in SEEDS:
            run_dir = after / arm / f"seed{seed}"
            for name in RUN_FILES:
                if not (run_dir / name).is_file():
                    errors.append(f"missing run artifact: {arm}/seed{seed}/{name}")
            if errors and not (run_dir / "results.json").is_file():
                continue
            try:
                result = _load(run_dir / "results.json")
                config = _load(run_dir / "config.json")
                provenance = _load(run_dir / "provenance.json")
                decisions = _load(run_dir / "ucr_decisions.json")
                trace_lines = [line for line in (run_dir / "tool_trace.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
            except (OSError, ValueError) as exc:
                errors.append(f"unreadable run {arm}/seed{seed}: {exc}")
                continue

            metric = result.get("metrics", {}).get("UCR", {})
            if not metric.get("activated") or metric.get("status") != "measured":
                errors.append(f"UCR not activated: {arm}/seed{seed}")
            else:
                measured_runs += 1
            if metric.get("denominator") != metric.get("supported", 0) + metric.get("unexecuted", 0):
                errors.append(f"invalid UCR denominator: {arm}/seed{seed}")
            if metric.get("numerator") != metric.get("unexecuted"):
                errors.append(f"invalid UCR numerator: {arm}/seed{seed}")
            if len(trace_lines) != 9:
                errors.append(f"expected 9 trace events: {arm}/seed{seed}")
            if any(not decision.get("text") or not decision.get("reason") for decision in decisions):
                errors.append(f"decision lacks text/reason: {arm}/seed{seed}")
            if arm == "no-rail":
                unexecuted_total += metric.get("unexecuted", 0)
            if arm == "full-rail" and not config.get("rail", {}).get("accepted"):
                errors.append(f"full rail did not accept evidence-safe output: seed{seed}")
            if not config.get("generation", {}).get("contract_satisfied"):
                errors.append(f"generation contract unsatisfied: {arm}/seed{seed}")
            for name in HASHED_FILES:
                expected = provenance.get("files", {}).get(name)
                if expected != _sha256(run_dir / name):
                    errors.append(f"provenance mismatch: {arm}/seed{seed}/{name}")

    if measured_runs != 9:
        errors.append(f"expected 9 measured UCR runs, found {measured_runs}")
    if unexecuted_total < 1:
        errors.append("no real unexecuted claim found in no-rail runs")

    if (after / "summary.json").is_file():
        summary = _load(after / "summary.json")
        if not summary.get("complete") or not summary.get("all_dimensions_activated"):
            errors.append("aggregate summary is incomplete or UCR is not activated")
    legacy_root = benchmark / "results" / "before" / "legacy_t4"
    legacy_count = sum((legacy_root / arm / f"seed{seed}" / "results.json").is_file() for arm in ARMS for seed in SEEDS)
    if legacy_count != 9:
        errors.append(f"expected 9 legacy before-results, found {legacy_count}")

    for relative in ROOT_CREDENTIAL_FILES:
        path = project_root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            errors.append(f"possible embedded credential: {relative}")

    return errors


def main() -> int:
    project_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    errors = verify_project(project_root)
    if errors:
        print("DELIVERY VERIFICATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("DELIVERY VERIFICATION PASSED")
    print("9/9 runs measured; provenance, evidence, aggregation, and credential checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
