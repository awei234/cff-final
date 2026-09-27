"""Typed boundary for constrained Harness manifests."""

from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = frozenset({"profile", "memory_mode", "planning_mode", "enabled_tools", "max_provider_calls", "max_retries", "selection_reason"})


def manifest_fields_present(manifest: dict[str, Any]) -> bool:
    return REQUIRED_FIELDS.issubset(manifest)
