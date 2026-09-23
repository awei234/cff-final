from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from competition_runner.cross_topic import REQUIRED_ARTIFACTS
from competition_runner.cross_topic_live import (
    CrossTopicLiveError,
    ProviderCommandCrossTopicBackend,
    execute_prepared_cross_topic_task,
    prepare_cross_topic_live_task,
    verify_cross_topic_run,
)


BASE = Path(__file__).resolve().parents[1]
FROZEN_PROTOCOL = BASE / "config" / "cross_topic_protocol_s4_v1.json"
PROVIDER_CONFIG = BASE / "config" / "providers.json"


class _ForbiddenEnvironment(dict):
    def get(self, key, default=None):
        raise AssertionError(f"credential read was not allowed: {key}")


def _prepare(tmp_path, *, task_id="context-engineering-glm-seed42", environ=None, max_calls=1):
    return prepare_cross_topic_live_task(
        protocol_path=FROZEN_PROTOCOL,
        provider_config_path=PROVIDER_CONFIG,
        output_root=tmp_path / "formal_runs",
        task_id=task_id,
        confirmed=True,
        max_calls=max_calls,
        environ=environ or {"ZHIPUAI_API_KEY": "selected-secret"},
    )


def _bundle() -> dict[str, object]:
    return {
        "prompt": "Frozen cross-topic prompt",
        "tool_events": [{"event_id": "tool-1", "status": "success"}],
        "results": {"claims": [], "measurements": [], "status": "completed"},
        "paper_tex": "\\documentclass{article}\n\\begin{document}Live evidence.\\end{document}\n",
        "resource": {"token_usage": 10, "duration_seconds": 1.5, "cost": None},
        "research_materials": {"items": []},
        "plan": {"steps": ["research", "write", "verify"]},
        "execution_report": {"status": "completed"},
        "rail_events": [{"event_id": "rail-1", "decision": "accepted"}],
        "human_interventions": [{"status": "none"}],
    }


def _write_adapter(
    path: Path,
    *,
    fail: bool = False,
    bundle: dict[str, object] | None = None,
) -> Path:
    if fail:
        source = "import sys\nsys.stderr.write('synthetic failure')\nraise SystemExit(7)\n"
    else:
        payload = json.dumps(bundle or _bundle(), ensure_ascii=False)
        source = f'''import json, os, sys
request = json.load(sys.stdin)
assert request["task"]["provider"] == "glm"
assert os.environ["OPENAI_COMPAT_API_KEY"] == "selected-secret"
assert "DASHSCOPE_API_KEY" not in os.environ
assert "DEEPSEEK_API_KEY" not in os.environ
assert os.environ["CROSS_TOPIC_CALL_LIMIT"] == "1"
print({payload!r})
'''
    path.write_text(source, encoding="utf-8")
    return path


def test_prepare_requires_confirmation_and_positive_cap_before_credentials(tmp_path):
    """Removing either authorization gate would permit an unapproved paid key read."""
    for confirmed, max_calls, expected in (
        (False, 1, "live_confirmation_required"),
        (True, 0, "call_limit_invalid"),
    ):
        with pytest.raises(CrossTopicLiveError) as exc:
            prepare_cross_topic_live_task(
                protocol_path=FROZEN_PROTOCOL,
                provider_config_path=PROVIDER_CONFIG,
                output_root=tmp_path / "formal_runs",
                task_id="context-engineering-glm-seed42",
                confirmed=confirmed,
                max_calls=max_calls,
                environ=_ForbiddenEnvironment(),
            )
        assert exc.value.code == expected
    assert not (tmp_path / "formal_runs").exists()


def test_prepare_blocks_deepseek_before_credentials_even_when_confirmed(tmp_path):
    """Changing the provider branch must never make a DeepSeek task key-readable."""
    with pytest.raises(CrossTopicLiveError) as exc:
        prepare_cross_topic_live_task(
            protocol_path=FROZEN_PROTOCOL,
            provider_config_path=PROVIDER_CONFIG,
            output_root=tmp_path / "formal_runs",
            task_id="context-engineering-deepseek-seed42",
            confirmed=True,
            max_calls=99,
            environ=_ForbiddenEnvironment(),
        )
    assert exc.value.code == "task_blocked_budget"
    assert not (tmp_path / "formal_runs").exists()


def test_prepare_rejects_provider_drift_and_selected_output_collision(tmp_path):
    """A changed provider or reused selected slot must fail before execution."""
    providers = json.loads(PROVIDER_CONFIG.read_text(encoding="utf-8"))
    providers["glm"]["model_id"] = "changed"
    changed = tmp_path / "providers.json"
    changed.write_text(json.dumps(providers), encoding="utf-8")
    with pytest.raises(CrossTopicLiveError) as drift:
        prepare_cross_topic_live_task(
            protocol_path=FROZEN_PROTOCOL,
            provider_config_path=changed,
            output_root=tmp_path / "formal_runs",
            task_id="context-engineering-glm-seed42",
            confirmed=True,
            max_calls=1,
            environ=_ForbiddenEnvironment(),
        )
    assert drift.value.code == "provider_config_drift"

    output_root = tmp_path / "occupied"
    selected = output_root / "context-engineering" / "glm" / "seed42"
    selected.mkdir(parents=True)
    marker = selected / "historical.txt"
    marker.write_text("keep", encoding="utf-8")
    with pytest.raises(CrossTopicLiveError) as collision:
        prepare_cross_topic_live_task(
            protocol_path=FROZEN_PROTOCOL,
            provider_config_path=PROVIDER_CONFIG,
            output_root=output_root,
            task_id="context-engineering-glm-seed42",
            confirmed=True,
            max_calls=1,
            environ=_ForbiddenEnvironment(),
        )
    assert collision.value.code == "formal_output_exists"
    assert marker.read_text(encoding="utf-8") == "keep"


def test_command_backend_isolates_provider_environment_and_enforces_cap(tmp_path):
    """Leaking other keys or permitting an extra subprocess would breach the paid-call boundary."""
    prepared = _prepare(
        tmp_path,
        environ={
            "ZHIPUAI_API_KEY": "selected-secret",
            "DASHSCOPE_API_KEY": "other-secret",
            "DEEPSEEK_API_KEY": "blocked-secret",
        },
    )
    backend = ProviderCommandCrossTopicBackend(
        command=[sys.executable, str(_write_adapter(tmp_path / "adapter.py"))],
        prepared=prepared,
        environ={
            "ZHIPUAI_API_KEY": "selected-secret",
            "DASHSCOPE_API_KEY": "other-secret",
            "DEEPSEEK_API_KEY": "blocked-secret",
        },
    )
    assert backend.generate(prepared["request"])["execution_report"]["status"] == "completed"
    with pytest.raises(CrossTopicLiveError) as cap:
        backend.generate(prepared["request"])
    assert cap.value.code == "call_limit_exceeded"
    assert backend.calls_made == 1


@pytest.mark.parametrize(
    ("provider_resource", "expected"),
    (
        (
            "GPU time: 1.5 seconds",
            {"raw_text": "GPU time: 1.5 seconds", "normalized_from": "string"},
        ),
        ('{"token_usage": 10}', {"token_usage": 10}),
    ),
)
def test_command_backend_normalizes_non_empty_string_resource(
    tmp_path,
    provider_resource,
    expected,
):
    """Provider text must remain attributable while satisfying the frozen object artifact contract."""
    prepared = _prepare(tmp_path)
    bundle = _bundle()
    bundle["resource"] = provider_resource
    backend = ProviderCommandCrossTopicBackend(
        command=[
            sys.executable,
            str(_write_adapter(tmp_path / "adapter.py", bundle=bundle)),
        ],
        prepared=prepared,
        environ={"ZHIPUAI_API_KEY": "selected-secret"},
    )

    assert backend.generate(prepared["request"])["resource"] == expected
    assert backend.calls_made == 1


def test_execute_writes_exact_verified_fourteen_artifact_contract(tmp_path):
    """Omitting a pipeline artifact or provenance hash must prevent completion."""
    prepared = _prepare(tmp_path)
    backend = ProviderCommandCrossTopicBackend(
        command=[sys.executable, str(_write_adapter(tmp_path / "adapter.py"))],
        prepared=prepared,
        environ={"ZHIPUAI_API_KEY": "selected-secret"},
    )
    report = execute_prepared_cross_topic_task(prepared=prepared, backend=backend)
    output = prepared["output_path"]
    assert report["valid"] is True
    assert {item.name for item in output.iterdir()} == set(REQUIRED_ARTIFACTS)
    assert verify_cross_topic_run(output, expected_task=prepared["task"])["valid"] is True
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert manifest["model_api_calls"] == 1
    assert manifest["authorized_call_limit"] == 1
    assert backend.calls_made == 1
    paper_tex = (output / "paper.tex").read_bytes()
    paper_pdf = (output / "paper.pdf").read_bytes()
    provenance = json.loads((output / "provenance.json").read_text(encoding="utf-8"))
    assert paper_pdf.startswith(b"%PDF-1.4")
    assert paper_pdf.endswith(b"%%EOF\n")
    assert provenance["pdf_derivation"] == {
        "method": "stdlib-latex-text-pdf-v1",
        "paper_tex_sha256": sha256(paper_tex).hexdigest().upper(),
    }


def test_execute_preserves_failure_audit_without_fabricating_paper(tmp_path):
    """A failed provider command must leave failure evidence and no claimed paper."""
    prepared = _prepare(tmp_path)
    backend = ProviderCommandCrossTopicBackend(
        command=[sys.executable, str(_write_adapter(tmp_path / "adapter.py", fail=True))],
        prepared=prepared,
        environ={"ZHIPUAI_API_KEY": "selected-secret"},
    )
    with pytest.raises(CrossTopicLiveError) as exc:
        execute_prepared_cross_topic_task(prepared=prepared, backend=backend)
    assert exc.value.code == "provider_command_failed"
    output = prepared["output_path"]
    assert {item.name for item in output.iterdir()} == {
        "run_manifest.json",
        "execution_report.json",
    }
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["failure_code"] == "provider_command_failed"
    assert not (output / "paper.tex").exists()
    assert not (output / "paper.pdf").exists()


def test_invalid_bundle_failure_preserves_redacted_response_diagnostics(tmp_path):
    prepared = _prepare(tmp_path)
    invalid = _bundle()
    invalid.pop("paper_tex")
    invalid["results"] = {"note": "selected-secret", "padding": "x" * 70000}
    backend = ProviderCommandCrossTopicBackend(
        command=[sys.executable, str(_write_adapter(tmp_path / "adapter.py", bundle=invalid))],
        prepared=prepared,
        environ={"ZHIPUAI_API_KEY": "selected-secret"},
    )
    with pytest.raises(CrossTopicLiveError) as exc:
        execute_prepared_cross_topic_task(prepared=prepared, backend=backend)
    assert exc.value.code == "bundle_invalid"
    output = prepared["output_path"]
    assert {item.name for item in output.iterdir()} == {
        "run_manifest.json", "execution_report.json",
    }
    report = json.loads((output / "execution_report.json").read_text(encoding="utf-8"))
    assert report["failure_message"] == "paper_tex must be non-empty text"
    assert report["provider_response_bytes"] > 65536
    assert report["provider_response_truncated"] is True
    assert report["provider_response_field_types"]["results"] == "object"
    assert "paper_tex" not in report["provider_response_field_types"]
    assert len(report["provider_response_sha256"]) == 64
    assert "selected-secret" not in report["provider_response_text"]
    assert "[REDACTED]" in report["provider_response_text"]
    assert not (output / "paper.tex").exists()
    assert not (output / "paper.pdf").exists()


def test_live_cli_refuses_unconfirmed_and_deepseek_without_outputs(tmp_path):
    """The operator entrypoint must expose both authorization gates before execution."""
    script = BASE / "run_cross_topic_live.py"
    common = [
        sys.executable,
        str(script),
        "--protocol",
        str(FROZEN_PROTOCOL),
        "--provider-config",
        str(PROVIDER_CONFIG),
        "--output-root",
        str(tmp_path / "formal_runs"),
        "--max-calls",
        "1",
    ]
    unconfirmed = subprocess.run(
        common + ["--task-id", "context-engineering-glm-seed42"],
        capture_output=True,
        text=True,
        shell=False,
    )
    deepseek = subprocess.run(
        common
        + [
            "--task-id",
            "context-engineering-deepseek-seed42",
            "--confirm-live",
        ],
        capture_output=True,
        text=True,
        shell=False,
    )
    assert unconfirmed.returncode == 2
    assert "live_confirmation_required" in unconfirmed.stderr
    assert deepseek.returncode == 2
    assert "task_blocked_budget" in deepseek.stderr
    assert not (tmp_path / "formal_runs").exists()
