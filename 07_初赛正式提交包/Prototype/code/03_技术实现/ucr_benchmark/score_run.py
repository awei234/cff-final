#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ucr_benchmark.experiment import score_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-score a stored UCR run from raw output and trace")
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(score_run(args.run_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
