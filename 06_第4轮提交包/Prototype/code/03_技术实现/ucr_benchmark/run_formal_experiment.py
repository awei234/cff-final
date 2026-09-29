#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from ucr_benchmark.formal_execution import (
    ProviderCommandModelAdapter,
    dry_run_formal_execution,
    execute_prepared_formal_task,
    prepare_formal_task,
)


BASE = Path(__file__).resolve().parent
PROJECT_ROOT = BASE.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run or preflight the frozen S3 formal UCR matrix"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--provider", choices=("glm", "qwen", "deepseek"))
    parser.add_argument("--task-id")
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=BASE / "config" / "formal_experiment_s3_v1.json",
    )
    parser.add_argument(
        "--provider-config",
        type=Path,
        default=PROJECT_ROOT
        / "03_技术实现"
        / "competition_runner"
        / "config"
        / "providers.json",
    )
    parser.add_argument(
        "--scenarios", type=Path, default=BASE / "config" / "scenarios.json"
    )
    parser.add_argument(
        "--output-root", type=Path, default=BASE / "results" / "formal_s3_v1"
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=BASE / "config" / "formal_execution_dry_run_s3_v1.json",
    )
    args = parser.parse_args()
    if args.execute and (not args.provider or not args.task_id or not args.confirm_live):
        parser.error("--execute requires --provider, --task-id, and --confirm-live")
    try:
        if args.dry_run:
            report = dry_run_formal_execution(
                manifest_path=args.manifest,
                provider_config_path=args.provider_config,
                scenario_path=args.scenarios,
                output_root=args.output_root,
                report_path=args.report,
            )
        else:
            prepared = prepare_formal_task(
                manifest_path=args.manifest,
                provider_config_path=args.provider_config,
                scenario_path=args.scenarios,
                output_root=args.output_root,
                task_id=args.task_id,
                environ=os.environ,
            )
            if prepared["task"]["provider"] != args.provider:
                raise ValueError("selected_provider_task_mismatch")
            adapter = ProviderCommandModelAdapter(
                command=[
                    sys.executable,
                    str(BASE / "adapters" / "openai_compatible.py"),
                ],
                prepared=prepared,
                environ=os.environ,
            )
            run_dir = execute_prepared_formal_task(
                prepared=prepared,
                adapter=adapter,
                scenario_path=args.scenarios,
            )
            report = {
                "mode": "live_execute",
                "task_id": args.task_id,
                "provider": args.provider,
                "run_dir": str(run_dir),
            }
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"[formal_execution_failed] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
