#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ucr_benchmark.aggregate import aggregate_runs
from ucr_benchmark.schema import write_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate complete UCR results (legacy three-arm or constrained-JIT four-arm)"
    )
    parser.add_argument("results_root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--seeds",
        default="42,43,44",
        help="Comma-separated seed list (default: 42,43,44)",
    )
    parser.add_argument(
        "--allow-not-applicable",
        action="store_true",
        help="Preserve legitimate not_applicable UCR values instead of failing",
    )
    args = parser.parse_args()
    try:
        seeds = tuple(int(value.strip()) for value in args.seeds.split(",") if value.strip())
    except ValueError:
        parser.error("--seeds must be a comma-separated list of integers")
    summary = aggregate_runs(
        args.results_root,
        seeds=seeds,
        allow_not_applicable=args.allow_not_applicable,
    )
    output = args.output or args.results_root / "summary.json"
    write_json(output, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
