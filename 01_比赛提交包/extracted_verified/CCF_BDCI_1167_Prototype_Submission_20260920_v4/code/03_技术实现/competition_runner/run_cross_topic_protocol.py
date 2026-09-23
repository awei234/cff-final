#!/usr/bin/env python3
"""Run the frozen cross-topic protocol gate in offline dry-run mode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from competition_runner.cross_topic_execution import (
    CrossTopicExecutionError,
    dry_run_cross_topic_protocol,
)


BASE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and classify the S4 cross-topic protocol offline"
    )
    parser.add_argument("--dry-run", action="store_true", required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=BASE / "config" / "cross_topic_protocol_s4_v1.json",
    )
    parser.add_argument(
        "--provider-config",
        type=Path,
        default=BASE / "config" / "providers.json",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=BASE / "results" / "formal_s4_v1",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=BASE / "config" / "cross_topic_execution_dry_run_s4_v1.json",
    )
    args = parser.parse_args()
    try:
        report = dry_run_cross_topic_protocol(
            protocol_path=args.protocol,
            provider_config_path=args.provider_config,
            output_root=args.output_root,
            report_path=args.report,
        )
    except CrossTopicExecutionError as exc:
        print(f"[{exc.code}] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
