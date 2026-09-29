#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from ucr_benchmark.jit_delivery import verify_jit_comparison


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a four-arm constrained-JIT comparison without modifying it"
    )
    parser.add_argument("results_root", type=Path)
    args = parser.parse_args()
    errors = verify_jit_comparison(args.results_root)
    if errors:
        print("JIT COMPARISON VERIFICATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("JIT COMPARISON VERIFICATION PASSED")
    print("12/12 runs verified; policies, budgets, rails, evidence, and hashes are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
