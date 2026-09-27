#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ucr_benchmark.experiment import ARMS, CommandModelAdapter, FixturePolicyAdapter, run_one


BASE = Path(__file__).resolve().parent


def preflight_run_directories(pairs: list[tuple[str, int]], output_root: Path) -> None:
    """Reject a batch before execution when any formal run target already exists."""
    for arm, seed in pairs:
        target = output_root / arm / f"seed{seed}"
        if target.exists():
            raise FileExistsError(f"refusing to overwrite existing run: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run evidence-backed UCR experiments")
    parser.add_argument("--all", action="store_true", help="run all four arms and seeds 42/43/44")
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--output", type=Path, default=BASE / "results" / "after")
    args = parser.parse_args()
    if not args.all and (args.arm is None or args.seed is None):
        parser.error("use --all or provide both --arm and --seed")
    pairs = [(arm, seed) for arm in ARMS for seed in (42, 43, 44)] if args.all else [(str(args.arm), int(args.seed))]
    preflight_run_directories(pairs, args.output)
    if args.mode == "fixture":
        adapter = FixturePolicyAdapter()
    else:
        command_json = os.environ.get("UCR_MODEL_COMMAND_JSON")
        model_id = os.environ.get("UCR_MODEL_ID")
        if not command_json or not model_id:
            parser.error("live mode requires UCR_MODEL_COMMAND_JSON and UCR_MODEL_ID")
        command = json.loads(command_json)
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            parser.error("UCR_MODEL_COMMAND_JSON must be a JSON array of strings")
        adapter = CommandModelAdapter(command, model_id=model_id)
    for arm, seed in pairs:
        path = run_one(arm, seed, adapter, args.output)
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
