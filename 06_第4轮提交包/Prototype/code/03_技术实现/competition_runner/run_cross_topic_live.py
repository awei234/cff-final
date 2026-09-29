#!/usr/bin/env python3
"""Execute one explicitly authorized frozen S4 cross-topic task."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from competition_runner.cross_topic_live import (
    CrossTopicLiveError,
    ProviderCommandCrossTopicBackend,
    execute_prepared_cross_topic_task,
    prepare_cross_topic_live_task,
)


BASE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one frozen S4 cross-topic task")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument("--max-calls", required=True, type=int)
    parser.add_argument("--protocol", type=Path, default=BASE / "config" / "cross_topic_protocol_s4_v1.json")
    parser.add_argument("--provider-config", type=Path, default=BASE / "config" / "providers.json")
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument(
        "--allow-deepseek-demo",
        action="store_true",
        help="explicitly enable the bounded DeepSeek context-engineering demo; disabled by default",
    )
    parser.add_argument(
        "--adapter",
        type=Path,
        default=BASE / "adapters" / "cross_topic_openai_compatible.py",
    )
    args = parser.parse_args()
    output_root = args.output_root
    if output_root is None:
        package_root = BASE.parents[2] if (BASE.parents[2] / "README.md").is_file() else BASE
        output_root = package_root / ("demo_runs" if args.allow_deepseek_demo else Path("results") / "formal_s4_v1")
    try:
        prepared = prepare_cross_topic_live_task(
            protocol_path=args.protocol,
            provider_config_path=args.provider_config,
            output_root=output_root,
            task_id=args.task_id,
            confirmed=args.confirm_live,
            max_calls=args.max_calls,
            environ=os.environ,
            allow_deepseek_demo=args.allow_deepseek_demo,
        )
        backend = ProviderCommandCrossTopicBackend(
            command=[sys.executable, str(args.adapter)],
            prepared=prepared,
            environ=os.environ,
        )
        report = execute_prepared_cross_topic_task(prepared=prepared, backend=backend)
    except CrossTopicLiveError as exc:
        print(f"[{exc.code}] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
