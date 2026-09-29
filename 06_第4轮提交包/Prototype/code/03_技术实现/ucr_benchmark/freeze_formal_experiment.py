#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from ucr_benchmark.formal_matrix import freeze_formal_matrix


BASE = Path(__file__).resolve().parent
PROJECT_ROOT = BASE.parents[1]


def _head_commit() -> str:
    completed = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        check=False,
        shell=False,
        text=True,
    )
    value = completed.stdout.strip()
    if completed.returncode != 0 or len(value) != 40:
        raise RuntimeError("unable to resolve the source commit")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze the S3 formal UCR matrix without calling model APIs"
    )
    parser.add_argument(
        "--provider-config",
        type=Path,
        default=PROJECT_ROOT / "03_技术实现" / "competition_runner" / "config" / "providers.json",
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=BASE / "config" / "scenarios.json",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=BASE / "results" / "formal_s3_v1",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=BASE / "config" / "formal_experiment_s3_v1.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=BASE / "config" / "formal_preflight_s3_v1.json",
    )
    parser.add_argument("--source-commit", default=None)
    args = parser.parse_args()
    try:
        report = freeze_formal_matrix(
            provider_config_path=args.provider_config,
            scenario_path=args.scenarios,
            source_commit=args.source_commit or _head_commit(),
            output_root=args.output_root,
            manifest_path=args.manifest,
            report_path=args.report,
        )
    except (FileExistsError, OSError, RuntimeError, ValueError) as exc:
        print(f"[formal_freeze_failed] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
