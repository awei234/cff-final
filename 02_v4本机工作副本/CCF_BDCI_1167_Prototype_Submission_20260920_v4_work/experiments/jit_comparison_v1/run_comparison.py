"""Run the fixed-vs-constrained Harness comparison on deterministic UCR fixtures."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
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
            run_one(raw_arm, seed, adapter, run_root)
            raw_dir = run_root / raw_arm / f"seed{seed}"
            arm_dir = output_root / f"seed-{seed}" / arm
            shutil.copytree(raw_dir, arm_dir)
            manifest = build_harness_manifest({"requires_evidence": True, "experiment_required": arm in {"full-rail", "jit-constrained"}})
            validation = validate_manifest(manifest)
            if arm == "jit-constrained":
                archive_run(arm_dir / "harness", manifest=validation.manifest, validation={"valid": validation.valid, "errors": list(validation.errors)}, metrics={"seed": seed, "arm": arm}, evidence=[{"artifact": "results.json"}])
            result = json.loads((arm_dir / "results.json").read_text(encoding="utf-8"))
            rows.append({"seed": seed, "arm": arm, "underlying_arm": raw_arm, "metrics": result.get("metrics", {}), "rail": result.get("rail", {}), "manifest": validation.manifest if arm == "jit-constrained" else None})
    summary = {"schema_version": "jit-comparison-v1", "arms": list(ARMS), "seeds": list(SEEDS), "results": rows, "gate": {"same_task": True, "same_model": True, "same_budget": True, "same_tools": True}}
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
    lines.extend(["", "The fixture measures process evidence behavior. It is not a domain effectiveness result."])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("demo_runs/jit_comparison_v1"))
    args = parser.parse_args()
    summary = run_comparison(args.output)
    print(json.dumps({"output": str(args.output.resolve()), "runs": len(summary["results"]), "arms": summary["arms"], "seeds": summary["seeds"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
