"""Deterministic planner entry point for the minimal JIT Harness pilot."""

from __future__ import annotations

from .selector import select_harness


def build_harness_manifest(task_features: dict[str, object]) -> dict[str, object]:
    """Build a manifest without executing code or expanding the tool set."""
    return select_harness(task_features)
