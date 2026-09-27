from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any, Sequence


LEGACY_ARMS = ("no-rail", "prompt-only", "full-rail")
ARMS = (*LEGACY_ARMS, "jit-constrained")
SEEDS = (42, 43, 44)


def _load(root: Path, arm: str, seed: int) -> dict[str, Any]:
    path = root / arm / f"seed{seed}" / "results.json"
    if not path.exists():
        raise ValueError(f"missing result: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("arm") != arm or int(result.get("seed", -1)) != seed:
        raise ValueError(f"result metadata mismatch: {path}")
    return result


def _wilson_interval(numerator: int, denominator: int) -> dict[str, Any] | None:
    if denominator <= 0:
        return None
    z = 1.959963984540054
    proportion = numerator / denominator
    scale = 1 + z * z / denominator
    centre = (proportion + z * z / (2 * denominator)) / scale
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / denominator
            + z * z / (4 * denominator * denominator)
        )
        / scale
    )
    return {
        "method": "wilson",
        "lower": round(max(0.0, centre - margin), 4),
        "upper": round(min(1.0, centre + margin), 4),
    }


def aggregate_runs(
    root: Path,
    *,
    seeds: Sequence[int] = SEEDS,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    selected_seeds = tuple(int(seed) for seed in seeds)
    if not selected_seeds or len(set(selected_seeds)) != len(selected_seeds):
        raise ValueError("seeds must be non-empty and unique")
    has_complete_jit_arm = all(
        (root / "jit-constrained" / f"seed{seed}" / "results.json").is_file()
        for seed in selected_seeds
    )
    selected_arms = ARMS if has_complete_jit_arm else LEGACY_ARMS
    loaded = {
        (arm, seed): _load(root, arm, seed)
        for arm in selected_arms
        for seed in selected_seeds
    }
    summary: dict[str, Any] = {
        "experiment": "ucr-activation-v1",
        "complete": True,
        "all_dimensions_activated": True,
        "arms": {},
        "paired_differences": {},
        "paired_comparable_seed_counts": {},
    }
    values: dict[str, list[float | None]] = {}
    for arm in selected_arms:
        arm_values: list[float | None] = []
        numerators: list[int] = []
        denominators: list[int] = []
        not_applicable_count = 0
        for seed in selected_seeds:
            metric = loaded[(arm, seed)]["metrics"]["UCR"]
            activated = bool(metric.get("activated"))
            if not activated:
                if allow_not_applicable and metric.get("status") == "not_applicable":
                    summary["all_dimensions_activated"] = False
                    not_applicable_count += 1
                    arm_values.append(None)
                    continue
                raise ValueError(f"UCR dimension is not activated: {arm} seed{seed}")
            if int(metric.get("denominator", 0)) <= 0 or metric.get("value") is None:
                raise ValueError(f"UCR dimension is not activated: {arm} seed{seed}")
            arm_values.append(float(metric["value"]))
            numerators.append(int(metric["numerator"]))
            denominators.append(int(metric["denominator"]))
        values[arm] = arm_values
        activated_values = [value for value in arm_values if value is not None]
        total_numerator = sum(numerators)
        total_denominator = sum(denominators)
        summary["arms"][arm] = {
            "seeds": list(selected_seeds),
            "UCR": {
                "per_seed": arm_values,
                "activated_seed_count": len(activated_values),
                "not_applicable_seed_count": not_applicable_count,
                "mean": (
                    round(statistics.fmean(activated_values), 4)
                    if activated_values
                    else None
                ),
                "std": (
                    round(statistics.pstdev(activated_values), 4)
                    if activated_values
                    else None
                ),
                "total_numerator": total_numerator,
                "total_denominator": total_denominator,
                "pooled_value": (
                    round(total_numerator / total_denominator, 4)
                    if total_denominator
                    else None
                ),
                "confidence_interval_95": _wilson_interval(
                    total_numerator, total_denominator
                ),
            },
        }
    pairs = [
        ("prompt-only", "no-rail"),
        ("full-rail", "no-rail"),
        ("full-rail", "prompt-only"),
    ]
    if has_complete_jit_arm:
        pairs.extend(
            [
                ("jit-constrained", "no-rail"),
                ("jit-constrained", "prompt-only"),
                ("jit-constrained", "full-rail"),
            ]
        )
    for left, right in pairs:
        key = f"{left}_minus_{right}"
        differences = [
            round(a - b, 4) if a is not None and b is not None else None
            for a, b in zip(values[left], values[right], strict=True)
        ]
        summary["paired_differences"][key] = differences
        summary["paired_comparable_seed_counts"][key] = sum(
            value is not None for value in differences
        )
    return summary
