from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest


BASE = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE.parents[1]
MANIFEST = BASE / "config" / "formal_experiment_s3_v1.json"
PROVIDERS = PROJECT_ROOT / "03_技术实现" / "competition_runner" / "config" / "providers.json"
SCENARIOS = BASE / "config" / "scenarios.json"


def test_dry_run_classifies_frozen_tasks_without_creating_results(tmp_path: Path) -> None:
    """Creating result directories or reporting calls would turn planning into false evidence."""
    try:
        from ucr_benchmark.formal_execution import dry_run_formal_execution
    except ImportError as exc:
        raise AssertionError("provider-aware formal dry-run is required") from exc

    output_root = tmp_path / "formal-results"
    report_path = tmp_path / "formal-dry-run.json"

    report = dry_run_formal_execution(
        manifest_path=MANIFEST,
        provider_config_path=PROVIDERS,
        scenario_path=SCENARIOS,
        output_root=output_root,
        report_path=report_path,
    )

    assert report["mode"] == "offline_dry_run"
    assert report["model_api_calls"] == 0
    assert report["results_written"] == 0
    assert report["task_counts"] == {
        "selected": 90,
        "eligible_not_executed": 60,
        "blocked_budget": 30,
    }
    assert report["provider_counts"] == {
        "glm": {"eligible_not_executed": 30},
        "qwen": {"eligible_not_executed": 30},
        "deepseek": {"blocked_budget": 30},
    }
    assert output_root.exists() is False
    assert json.loads(report_path.read_text(encoding="utf-8")) == report


def test_dry_run_rejects_provider_drift_before_writing_report(tmp_path: Path) -> None:
    """A changed model ID must not silently replace the frozen experimental input."""
    from ucr_benchmark.formal_execution import dry_run_formal_execution

    providers = json.loads(PROVIDERS.read_text(encoding="utf-8"))
    providers["glm"]["model_id"] = "different-model"
    changed_provider_path = tmp_path / "providers.json"
    changed_provider_path.write_text(
        json.dumps(providers, ensure_ascii=False), encoding="utf-8"
    )
    report_path = tmp_path / "must-not-exist.json"

    with pytest.raises(ValueError, match="provider_config_hash_mismatch"):
        dry_run_formal_execution(
            manifest_path=MANIFEST,
            provider_config_path=changed_provider_path,
            scenario_path=SCENARIOS,
            output_root=tmp_path / "formal-results",
            report_path=report_path,
        )

    assert report_path.exists() is False


def test_dry_run_rejects_scenario_drift_before_writing_report(tmp_path: Path) -> None:
    """Changed scenario events would break the frozen same-input comparison."""
    from ucr_benchmark.formal_execution import dry_run_formal_execution

    changed_scenarios = tmp_path / "scenarios.json"
    changed_scenarios.write_bytes(SCENARIOS.read_bytes() + b"\n")
    report_path = tmp_path / "must-not-exist.json"

    with pytest.raises(ValueError, match="scenario_hash_mismatch"):
        dry_run_formal_execution(
            manifest_path=MANIFEST,
            provider_config_path=PROVIDERS,
            scenario_path=changed_scenarios,
            output_root=tmp_path / "formal-results",
            report_path=report_path,
        )

    assert report_path.exists() is False


def test_prepare_task_blocks_deepseek_even_when_a_key_is_present(tmp_path: Path) -> None:
    """Budget status, not credential availability, controls DeepSeek execution."""
    try:
        from ucr_benchmark.formal_execution import prepare_formal_task
    except ImportError as exc:
        raise AssertionError("formal task preparation is required") from exc

    with pytest.raises(ValueError, match="task_blocked_budget"):
        prepare_formal_task(
            manifest_path=MANIFEST,
            provider_config_path=PROVIDERS,
            scenario_path=SCENARIOS,
            output_root=tmp_path / "formal-results",
            task_id="deepseek-no-rail-seed42",
            environ={"DEEPSEEK_API_KEY": "present-but-must-not-be-used"},
        )

    assert (tmp_path / "formal-results").exists() is False


def test_prepare_task_routes_frozen_provider_without_exposing_key(tmp_path: Path) -> None:
    """Wrong provider routing or serialized credentials would invalidate formal evidence."""
    from ucr_benchmark.formal_execution import prepare_formal_task

    secret = "do-not-serialize-this-key"
    prepared = prepare_formal_task(
        manifest_path=MANIFEST,
        provider_config_path=PROVIDERS,
        scenario_path=SCENARIOS,
        output_root=tmp_path / "formal-results",
        task_id="glm-full-rail-seed47",
        environ={"ZHIPUAI_API_KEY": secret},
    )

    assert prepared["task"]["provider"] == "glm"
    assert prepared["task"]["model_id"] == "glm-5.2"
    assert prepared["task"]["temperature"] == 0.2
    assert prepared["task"]["max_tokens"] == 4096
    assert prepared["provider"] == {
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "model_id": "glm-5.2",
        "api_key_env": "ZHIPUAI_API_KEY",
        "api_key_present": True,
    }
    assert prepared["output_path"] == tmp_path / "formal-results" / "glm" / "full-rail" / "seed47"
    assert secret not in json.dumps(prepared, ensure_ascii=False, default=str)


def test_prepare_task_rejects_selected_output_collision(tmp_path: Path) -> None:
    """A second formal attempt must stop before it can overwrite prior evidence."""
    from ucr_benchmark.formal_execution import prepare_formal_task

    output_root = tmp_path / "formal-results"
    target = output_root / "qwen" / "prompt-only" / "seed49"
    target.mkdir(parents=True)
    marker = target / "historical.txt"
    marker.write_text("keep\n", encoding="utf-8")

    with pytest.raises(ValueError, match="formal_output_exists"):
        prepare_formal_task(
            manifest_path=MANIFEST,
            provider_config_path=PROVIDERS,
            scenario_path=SCENARIOS,
            output_root=output_root,
            task_id="qwen-prompt-only-seed49",
            environ={"DASHSCOPE_API_KEY": "present"},
        )

    assert marker.read_text(encoding="utf-8") == "keep\n"


def test_prepare_task_rejects_a_tampered_frozen_matrix(tmp_path: Path) -> None:
    """Selecting one task must not bypass integrity checks over the frozen matrix."""
    from ucr_benchmark.formal_execution import prepare_formal_task

    matrix = json.loads(MANIFEST.read_text(encoding="utf-8"))
    matrix["tasks"][0]["temperature"] = 0.9
    changed_manifest = tmp_path / "tampered-matrix.json"
    changed_manifest.write_text(
        json.dumps(matrix, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="formal_matrix_invalid"):
        prepare_formal_task(
            manifest_path=changed_manifest,
            provider_config_path=PROVIDERS,
            scenario_path=SCENARIOS,
            output_root=tmp_path / "formal-results",
            task_id="qwen-no-rail-seed42",
            environ={"DASHSCOPE_API_KEY": "present"},
        )


def test_prepare_task_allows_a_different_completed_slot(tmp_path: Path) -> None:
    """Sequential formal runs must only collision-check the selected output slot."""
    from ucr_benchmark.formal_execution import prepare_formal_task

    output_root = tmp_path / "formal-results"
    completed = output_root / "glm" / "no-rail" / "seed42"
    completed.mkdir(parents=True)
    (completed / "results.json").write_text("{}\n", encoding="utf-8")

    prepared = prepare_formal_task(
        manifest_path=MANIFEST,
        provider_config_path=PROVIDERS,
        scenario_path=SCENARIOS,
        output_root=output_root,
        task_id="glm-no-rail-seed43",
        environ={"ZHIPUAI_API_KEY": "present"},
    )

    assert prepared["output_path"] == output_root / "glm" / "no-rail" / "seed43"


class _DeterministicGlmAdapter:
    model_id = "glm-5.2"

    def generate(self, prompt: str, config: dict[str, object]) -> str:
        return "\n".join(
            [
                "We ran the checksum script [op:run_success].",
                "We inspected the observations file [op:inspect_existing].",
                "We queried the local source record [op:query_available].",
                "We validated the control artifact [op:validate_success].",
            ]
        )


def test_execute_task_records_frozen_provider_and_generation_parameters(tmp_path: Path) -> None:
    """Formal output must identify the frozen task rather than a generic legacy run."""
    try:
        from ucr_benchmark.formal_execution import (
            execute_prepared_formal_task,
            prepare_formal_task,
        )
    except ImportError as exc:
        raise AssertionError("formal task execution is required") from exc

    output_root = tmp_path / "formal-results"
    prepared = prepare_formal_task(
        manifest_path=MANIFEST,
        provider_config_path=PROVIDERS,
        scenario_path=SCENARIOS,
        output_root=output_root,
        task_id="glm-no-rail-seed42",
        environ={"ZHIPUAI_API_KEY": "present"},
    )

    run_dir = execute_prepared_formal_task(
        prepared=prepared,
        adapter=_DeterministicGlmAdapter(),
        scenario_path=SCENARIOS,
    )

    assert run_dir == output_root / "glm" / "no-rail" / "seed42"
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert config["model"] == "glm-5.2"
    assert config["generation"]["temperature"] == 0.2
    assert config["generation"]["max_tokens"] == 4096
    assert config["formal"] == {
        "experiment_id": "ucr-formal-s3-v1",
        "task_id": "glm-no-rail-seed42",
        "provider": "glm",
        "input_sha256": "B2381142DE4BA56CDA41B4DF61F79118001C230ED035810167D70C6FDEE29467",
        "source_commit": "fe0330b45cb14944d4cde687ff8382d078909cac",
        "output_relpath": "glm/no-rail/seed42",
    }


def test_provider_adapter_passes_frozen_runtime_only_to_subprocess(tmp_path: Path) -> None:
    """A provider command must receive the selected task settings without using a shell."""
    try:
        from ucr_benchmark.formal_execution import (
            ProviderCommandModelAdapter,
            prepare_formal_task,
        )
    except ImportError as exc:
        raise AssertionError("provider command adapter is required") from exc

    secret = "memory-only-test-key"
    prepared = prepare_formal_task(
        manifest_path=MANIFEST,
        provider_config_path=PROVIDERS,
        scenario_path=SCENARIOS,
        output_root=tmp_path / "formal-results",
        task_id="qwen-prompt-only-seed50",
        environ={"DASHSCOPE_API_KEY": secret},
    )
    command = [
        sys.executable,
        "-c",
        (
            "import json,os,sys; "
            "print(json.dumps({'base':os.environ['OPENAI_COMPAT_API_BASE'],"
            "'key':os.environ['OPENAI_COMPAT_API_KEY'],"
            "'model':os.environ['OPENAI_COMPAT_MODEL'],"
            "'arm':os.environ['UCR_ARM'],'seed':os.environ['UCR_SEED'],"
            "'temperature':os.environ['UCR_TEMPERATURE'],"
            "'max_tokens':os.environ['UCR_MAX_TOKENS'],"
            "'prompt':sys.stdin.read()}))"
        ),
    ]
    adapter = ProviderCommandModelAdapter(
        command=command,
        prepared=prepared,
        environ={"DASHSCOPE_API_KEY": secret},
    )

    output = json.loads(
        adapter.generate(
            "offline prompt",
            {
                "arm": "prompt-only",
                "seed": 50,
                "generation": {"temperature": 0.2, "max_tokens": 4096},
            },
        )
    )

    assert output == {
        "base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "key": secret,
        "model": "qwen-plus",
        "arm": "prompt-only",
        "seed": "50",
        "temperature": "0.2",
        "max_tokens": "4096",
        "prompt": "offline prompt",
    }


def test_provider_adapter_scrubs_raw_provider_keys_from_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A selected provider process must not inherit credentials for other providers."""
    from ucr_benchmark.formal_execution import (
        ProviderCommandModelAdapter,
        prepare_formal_task,
    )

    monkeypatch.setenv("ZHIPUAI_API_KEY", "unrelated-glm-secret")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "selected-qwen-secret")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "blocked-deepseek-secret")
    prepared = prepare_formal_task(
        manifest_path=MANIFEST,
        provider_config_path=PROVIDERS,
        scenario_path=SCENARIOS,
        output_root=tmp_path / "formal-results",
        task_id="qwen-no-rail-seed42",
        environ=dict(os.environ),
    )
    command = [
        sys.executable,
        "-c",
        (
            "import json,os; print(json.dumps({name:(name in os.environ) "
            "for name in ['ZHIPUAI_API_KEY','DASHSCOPE_API_KEY','DEEPSEEK_API_KEY']}))"
        ),
    ]
    adapter = ProviderCommandModelAdapter(
        command=command,
        prepared=prepared,
        environ=dict(os.environ),
    )

    inherited = json.loads(
        adapter.generate(
            "offline prompt",
            {
                "arm": "no-rail",
                "seed": 42,
                "generation": {"temperature": 0.2, "max_tokens": 4096},
            },
        )
    )

    assert inherited == {
        "ZHIPUAI_API_KEY": False,
        "DASHSCOPE_API_KEY": False,
        "DEEPSEEK_API_KEY": False,
    }


def test_openai_compatible_payload_uses_frozen_generation_parameters() -> None:
    """Ignoring max_tokens or seed would make providers run under different protocols."""
    try:
        from adapters.openai_compatible import build_request_payload
    except ImportError as exc:
        raise AssertionError("parameterized OpenAI-compatible payload is required") from exc

    payload = build_request_payload(
        prompt="formal prompt",
        model="qwen-plus",
        seed=50,
        temperature=0.2,
        max_tokens=4096,
    )

    assert payload == {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": "formal prompt"}],
        "temperature": 0.2,
        "max_tokens": 4096,
        "seed": 50,
    }


def test_formal_cli_dry_run_writes_only_a_zero_call_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The public dry-run command must not share the live execution branch."""
    try:
        import run_formal_experiment
    except ImportError as exc:
        raise AssertionError("formal benchmark CLI is required") from exc

    output_root = tmp_path / "formal-results"
    report_path = tmp_path / "formal-dry-run.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_formal_experiment.py",
            "--dry-run",
            "--manifest",
            str(MANIFEST),
            "--provider-config",
            str(PROVIDERS),
            "--scenarios",
            str(SCENARIOS),
            "--output-root",
            str(output_root),
            "--report",
            str(report_path),
        ],
    )

    assert run_formal_experiment.main() == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["model_api_calls"] == 0
    assert report["results_written"] == 0
    assert output_root.exists() is False


def test_formal_cli_execute_still_blocks_deepseek_with_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The live CLI must not turn an explicit confirmation into a budget override."""
    import run_formal_experiment

    output_root = tmp_path / "formal-results"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "present-but-blocked")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_formal_experiment.py",
            "--execute",
            "--provider",
            "deepseek",
            "--task-id",
            "deepseek-no-rail-seed42",
            "--confirm-live",
            "--manifest",
            str(MANIFEST),
            "--provider-config",
            str(PROVIDERS),
            "--scenarios",
            str(SCENARIOS),
            "--output-root",
            str(output_root),
        ],
    )

    assert run_formal_experiment.main() == 2
    assert "task_blocked_budget" in capsys.readouterr().err
    assert output_root.exists() is False
