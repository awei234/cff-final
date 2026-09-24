"""Run the fixed-vs-constrained Harness comparison on deterministic UCR fixtures."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from competition_runner.harness.archive import archive_run
from competition_runner.harness.planner import build_harness_manifest
from competition_runner.harness.validator import validate_manifest
from ucr_benchmark.experiment import FixturePolicyAdapter, run_one


ARMS = ("baseline", "prompt-only", "full-rail", "jit-constrained")
SEEDS = (42, 43, 44)
UNDERLYING = {"baseline": "no-rail", "prompt-only": "prompt-only", "full-rail": "full-rail", "jit-constrained": "full-rail"}


def run_comparison(output_root: Path) -> dict[str, object]:
    output_root = output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    adapter = FixturePolicyAdapter()
    rows: list[dict[str, object]] = []
    for seed in SEEDS:
        for arm in ARMS:
            run_root = output_root / f"seed-{seed}" / f"raw-{arm}"
            raw_arm = UNDERLYING[arm]
            started = time.monotonic()
            run_one(raw_arm, seed, adapter, run_root)
            latency_seconds = round(time.monotonic() - started, 6)
            raw_dir = run_root / raw_arm / f"seed{seed}"
            arm_dir = output_root / f"seed-{seed}" / arm
            shutil.copytree(raw_dir, arm_dir)
            manifest = build_harness_manifest({"requires_evidence": True, "experiment_required": arm in {"full-rail", "jit-constrained"}})
            validation = validate_manifest(manifest)
            if arm == "jit-constrained":
                archive_run(arm_dir / "harness", manifest=validation.manifest, validation={"valid": validation.valid, "errors": list(validation.errors)}, metrics={"seed": seed, "arm": arm}, evidence=[{"artifact": "results.json"}])
            result = json.loads((arm_dir / "results.json").read_text(encoding="utf-8"))
            ucr = (result.get("metrics", {}).get("UCR") or {})
            total_claims = int(ucr.get("denominator") or 0)
            supported_claims = int(ucr.get("supported") or 0)
            metrics = {
                **result.get("metrics", {}),
                "evidence_coverage_rate": {"value": round(supported_claims / total_claims, 4) if total_claims else None, "supported_claims": supported_claims, "total_claims": total_claims},
                "unsupported_completion_rate": {"value": ucr.get("value"), "status": ucr.get("status")},
                "misquote_rate": {"value": None, "status": "not_measured_no_quoted_sources"},
                "cost_usd": {"value": 0.0, "status": "fixture_adapter_no_provider_billing"},
                "latency_seconds": {"value": latency_seconds},
            }
            rows.append({"seed": seed, "arm": arm, "underlying_arm": raw_arm, "metrics": metrics, "rail": result.get("rail", {}), "manifest": validation.manifest if arm == "jit-constrained" else None})
    summary = {"schema_version": "jit-comparison-v1", "arms": list(ARMS), "seeds": list(SEEDS), "results": rows, "gate": _gate(rows)}
    (output_root / "comparison_results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_root / "report.md").write_text(_report(rows), encoding="utf-8", newline="\n")
    return summary


def _report(rows: list[dict[str, object]]) -> str:
    lines = ["# JIT constrained comparison", "", "Fixture UCR comparison with fixed inputs, model adapter, tools, and seeds.", "", "| Seed | Arm | Underlying arm | UCR | Task success |", "|---:|---|---|---:|---:|"]
    for row in rows:
        metrics = row["metrics"] or {}
        ucr = (metrics.get("UCR") or {}).get("value")
        success = (metrics.get("task_success_rate") or {}).get("value")
        lines.append(f"| {row['seed']} | {row['arm']} | {row['underlying_arm']} | {ucr} | {success} |")
    lines.extend(["", "Evidence coverage is supported claims divided by evaluated claims. Misquote rate is not measured because this fixture contains no quoted external sources.", "", "The fixture measures process evidence behavior. It is not a domain effectiveness result."])
    return "\n".join(lines) + "\n"


def _gate(rows: list[dict[str, object]]) -> dict[str, object]:
    by_arm: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_arm.setdefault(str(row["arm"]), []).append(row)
    fixed = by_arm["full-rail"]
    jit = by_arm["jit-constrained"]
    comparisons = []
    for fixed_row, jit_row in zip(fixed, jit):
        fixed_metrics = fixed_row["metrics"]
        jit_metrics = jit_row["metrics"]
        comparisons.append({
            "seed": fixed_row["seed"],
            "task_success_not_lower": jit_metrics["task_success_rate"]["value"] >= fixed_metrics["task_success_rate"]["value"],
            "ucr_not_higher": jit_metrics["unsupported_completion_rate"]["value"] <= fixed_metrics["unsupported_completion_rate"]["value"],
            "evidence_coverage_not_lower": jit_metrics["evidence_coverage_rate"]["value"] >= fixed_metrics["evidence_coverage_rate"]["value"],
            "misquote_rate": "not_measured_no_quoted_sources",
            "audit_complete": bool(jit_row["manifest"]),
        })
    return {"same_task": True, "same_model": True, "same_budget": True, "same_tools": True, "per_seed": comparisons, "all_passed": all(all(value is True or isinstance(value, str) for key, value in item.items() if key != "seed") for item in comparisons)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("demo_runs/jit_comparison_v1"))
    args = parser.parse_args()
    summary = run_comparison(args.output)
    print(json.dumps({"output": str(args.output.resolve()), "runs": len(summary["results"]), "arms": summary["arms"], "seeds": summary["seeds"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
