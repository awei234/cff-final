from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parents[1]


def _canonical_sha256(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest().upper()


def test_builds_exact_budget_aware_ninety_task_matrix() -> None:
    try:
        from ucr_benchmark.formal_matrix import build_formal_matrix
    except ImportError as exc:
        raise AssertionError("formal matrix builder is required") from exc

    matrix = build_formal_matrix(
        provider_config_path=BASE.parent / "competition_runner" / "config" / "providers.json",
        scenario_path=BASE / "config" / "scenarios.json",
        source_commit="7" * 40,
    )
    tasks = matrix["tasks"]

    assert len(tasks) == 90
    assert len({task["task_id"] for task in tasks}) == 90
    assert Counter(task["provider"] for task in tasks) == {
        "glm": 30,
        "qwen": 30,
        "deepseek": 30,
    }
    assert Counter(task["arm"] for task in tasks) == {
        "no-rail": 30,
        "prompt-only": 30,
        "full-rail": 30,
    }
    assert Counter(task["status"] for task in tasks) == {
        "pending": 60,
        "blocked_budget": 30,
    }
    assert {task["seed"] for task in tasks} == set(range(42, 52))
    assert {task["model_id"] for task in tasks if task["provider"] == "glm"} == {
        "glm-5.2"
    }
    assert {task["model_id"] for task in tasks if task["provider"] == "qwen"} == {
        "qwen-plus"
    }
    assert matrix["parameters"] == {"temperature": 0.2, "max_tokens": 4096}


def test_validator_rejects_a_task_changed_after_freeze(tmp_path: Path) -> None:
    try:
        from ucr_benchmark.formal_matrix import (
            build_formal_matrix,
            validate_formal_matrix,
        )
    except ImportError as exc:
        raise AssertionError("formal matrix validator is required") from exc

    matrix = build_formal_matrix(
        provider_config_path=BASE.parent / "competition_runner" / "config" / "providers.json",
        scenario_path=BASE / "config" / "scenarios.json",
        source_commit="7" * 40,
    )
    tampered = deepcopy(matrix)
    tampered["tasks"][0]["seed"] = 99

    report = validate_formal_matrix(tampered, output_root=tmp_path / "formal-runs")

    assert report["valid"] is False
    assert "task_input_hash_mismatch" in report["errors"]


def test_validator_rejects_an_existing_formal_output_directory(tmp_path: Path) -> None:
    from ucr_benchmark.formal_matrix import build_formal_matrix, validate_formal_matrix

    matrix = build_formal_matrix(
        provider_config_path=BASE.parent / "competition_runner" / "config" / "providers.json",
        scenario_path=BASE / "config" / "scenarios.json",
        source_commit="7" * 40,
    )
    output_root = tmp_path / "formal-runs"
    existing = output_root / matrix["tasks"][0]["output_relpath"]
    existing.mkdir(parents=True)

    report = validate_formal_matrix(matrix, output_root=output_root)

    assert report["valid"] is False
    assert report["existing_outputs"] == [matrix["tasks"][0]["output_relpath"]]
    assert "formal_output_exists" in report["errors"]


def test_validator_rejects_unblocked_deepseek_task(tmp_path: Path) -> None:
    from ucr_benchmark.formal_matrix import build_formal_matrix, validate_formal_matrix

    matrix = build_formal_matrix(
        provider_config_path=BASE.parent / "competition_runner" / "config" / "providers.json",
        scenario_path=BASE / "config" / "scenarios.json",
        source_commit="7" * 40,
    )
    deepseek_task = next(
        task for task in matrix["tasks"] if task["provider"] == "deepseek"
    )
    deepseek_task["status"] = "pending"

    report = validate_formal_matrix(matrix, output_root=tmp_path / "formal-runs")

    assert report["valid"] is False
    assert "blocked_provider_executable" in report["errors"]


def test_validator_rejects_rehashed_incomplete_matrix(tmp_path: Path) -> None:
    from ucr_benchmark.formal_matrix import build_formal_matrix, validate_formal_matrix

    matrix = build_formal_matrix(
        provider_config_path=BASE.parent / "competition_runner" / "config" / "providers.json",
        scenario_path=BASE / "config" / "scenarios.json",
        source_commit="7" * 40,
    )
    matrix["tasks"].pop()
    matrix["tasks_sha256"] = _canonical_sha256(matrix["tasks"])

    report = validate_formal_matrix(matrix, output_root=tmp_path / "formal-runs")

    assert report["valid"] is False
    assert "formal_matrix_incomplete" in report["errors"]


def test_freeze_writes_once_without_overwriting_evidence(tmp_path: Path) -> None:
    try:
        from ucr_benchmark.formal_matrix import freeze_formal_matrix
    except ImportError as exc:
        raise AssertionError("exclusive formal matrix freeze is required") from exc

    manifest_path = tmp_path / "formal_experiment_s3_v1.json"
    report_path = tmp_path / "formal_preflight_s3_v1.json"
    kwargs = {
        "provider_config_path": BASE.parent
        / "competition_runner"
        / "config"
        / "providers.json",
        "scenario_path": BASE / "config" / "scenarios.json",
        "source_commit": "7" * 40,
        "output_root": tmp_path / "formal-runs",
        "manifest_path": manifest_path,
        "report_path": report_path,
    }

    report = freeze_formal_matrix(**kwargs)
    original_manifest = manifest_path.read_bytes()
    original_report = report_path.read_bytes()

    assert report["valid"] is True
    assert report["task_counts"] == {"total": 90, "pending": 60, "blocked_budget": 30}
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["tasks_sha256"]
    with pytest.raises(FileExistsError):
        freeze_formal_matrix(**kwargs)
    assert manifest_path.read_bytes() == original_manifest
    assert report_path.read_bytes() == original_report
