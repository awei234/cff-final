#!/usr/bin/env python3
"""Portable configuration, provider, and output-safety entry point."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from competition_runner.generation import FixtureBackend, GenerationError, GenerationRequest, generate_run
from competition_runner.output_guard import OutputGuardError, reserve_output_directory
from competition_runner.paths import PathConfigError, resolve_paths
from competition_runner.providers import ProviderConfigError, resolve_provider
from competition_runner.smoke import SmokeError, run_live_smoke, write_evidence_exclusive
from competition_runner.verification import verify_run


RUNNER_DIR = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="competition-runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    paths_parser = subparsers.add_parser("paths", help="resolve portable project paths")
    paths_parser.add_argument("--config")
    paths_parser.add_argument("--project-root")
    paths_parser.add_argument("--workspace-root")
    paths_parser.add_argument("--output-root")
    paths_parser.add_argument("--experiment-script")
    paths_parser.add_argument("--jiuwenswarm-command")

    provider_parser = subparsers.add_parser("provider-check", help="show a redacted provider tuple")
    provider_parser.add_argument("--provider", required=True, choices=("glm", "qwen", "deepseek"))
    provider_parser.add_argument("--config", default=str(RUNNER_DIR / "config" / "providers.json"))
    provider_parser.add_argument("--api-base")
    provider_parser.add_argument("--model")

    smoke_parser = subparsers.add_parser("live-smoke", help="perform one minimal live provider request")
    smoke_parser.add_argument("--provider", required=True, choices=("glm", "qwen", "deepseek"))
    smoke_parser.add_argument("--config", default=str(RUNNER_DIR / "config" / "providers.json"))
    smoke_parser.add_argument("--api-base")
    smoke_parser.add_argument("--model")
    smoke_parser.add_argument("--output", required=True)
    smoke_parser.add_argument("--timeout", type=int, default=30)

    reserve_parser = subparsers.add_parser("reserve-output", help="reserve one new formal run directory")
    reserve_parser.add_argument("--output-root", required=True)
    reserve_parser.add_argument("--run-id", required=True)

    generate_parser = subparsers.add_parser("generate", help="generate one immutable formal run")
    generate_parser.add_argument("--topic", required=True)
    generate_parser.add_argument("--provider", required=True, choices=("glm", "qwen", "deepseek"))
    generate_parser.add_argument("--model", required=True)
    generate_parser.add_argument("--seed", required=True, type=int)
    generate_parser.add_argument("--output", required=True)
    generate_parser.add_argument("--mode", choices=("live", "fixture"), default="live")
    generate_parser.add_argument("--config", default=str(RUNNER_DIR / "config" / "providers.json"))

    verify_parser = subparsers.add_parser("verify", help="verify an existing formal run without modifying it")
    verify_parser.add_argument("--run", required=True)
    return parser


def _source_commit() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(RUNNER_DIR.parents[1]), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            shell=False,
            check=False,
        )
    except OSError:
        return None
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and len(value) == 40 else None


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "paths":
            overrides = {
                "workspace_root": args.workspace_root,
                "output_root": args.output_root,
                "experiment_script": args.experiment_script,
                "jiuwenswarm_command": args.jiuwenswarm_command,
            }
            report = resolve_paths(
                anchor=RUNNER_DIR,
                project_root=args.project_root,
                config_path=args.config,
                overrides=overrides,
            ).as_report()
        elif args.command == "provider-check":
            report = resolve_provider(
                provider=args.provider,
                config_path=args.config,
                api_base=args.api_base,
                model_id=args.model,
            ).as_report()
        elif args.command == "reserve-output":
            target = reserve_output_directory(Path(args.output_root), args.run_id)
            report = {
                "created": True,
                "output_directory": str(target),
                "run_id": args.run_id,
            }
        elif args.command == "generate":
            provider = resolve_provider(
                provider=args.provider,
                config_path=args.config,
                model_id=args.model,
            )
            request = GenerationRequest(
                topic=args.topic,
                provider=provider.provider,
                model=provider.model_id,
                seed=args.seed,
                mode=args.mode,
                output=Path(args.output),
                source_commit=_source_commit(),
            )
            backend = FixtureBackend() if args.mode == "fixture" else None
            report = generate_run(request, backend=backend)
        elif args.command == "verify":
            run_path = Path(args.run)
            if not run_path.is_dir():
                print(f"[run_unreadable] run path is not a readable directory: {run_path}", file=sys.stderr)
                return 3
            result = verify_run(run_path)
            report = result.as_report()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if result.valid else 2
        else:
            provider = resolve_provider(
                provider=args.provider,
                config_path=args.config,
                api_base=args.api_base,
                model_id=args.model,
            )
            try:
                api_key = provider.load_api_key()
                report = run_live_smoke(provider, api_key, timeout_seconds=args.timeout)
            except (ProviderConfigError, SmokeError) as exc:
                failure_report = {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "provider": provider.provider,
                    "api_base": provider.api_base,
                    "api_key_source": f"env:{provider.api_key_env}",
                    "requested_model": provider.model_id,
                    "returned_model": None,
                    "success": False,
                    "mode": "live",
                    "error_category": exc.code,
                }
                write_evidence_exclusive(Path(args.output), failure_report)
                print(f"[{exc.code}] {exc}", file=sys.stderr)
                return 2
            write_evidence_exclusive(Path(args.output), report)
    except (GenerationError, OutputGuardError, PathConfigError, ProviderConfigError, SmokeError) as exc:
        print(f"[{exc.code}] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
