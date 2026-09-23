from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import main as runner_main


RUNNER_DIR = Path(__file__).resolve().parents[1]
MAIN = RUNNER_DIR / "main.py"


def test_paths_command_works_outside_repository(tmp_path):
    """The formal CLI must not depend on its launch directory."""
    completed = subprocess.run(
        [sys.executable, str(MAIN), "paths"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        shell=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["experiment_script"]["exists"] is True


def test_provider_check_never_prints_secret(tmp_path):
    """Diagnostic output must remain safe even when a key is present."""
    secret = "synthetic-cli-secret-that-must-not-appear"
    env = os.environ.copy()
    env["ZHIPUAI_API_KEY"] = secret
    completed = subprocess.run(
        [sys.executable, str(MAIN), "provider-check", "--provider", "glm"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        shell=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert secret not in completed.stdout
    assert secret not in completed.stderr
    report = json.loads(completed.stdout)
    assert report["api_key_source"] == "env:ZHIPUAI_API_KEY"
    assert report["api_key_present"] is True


def test_live_smoke_command_writes_new_sanitized_evidence(tmp_path, monkeypatch):
    """The CLI must connect provider resolution to an exclusive evidence artifact."""
    secret = "synthetic-live-cli-secret"
    monkeypatch.setenv("ZHIPUAI_API_KEY", secret)
    output = tmp_path / "live.jsonl"
    captured = {}

    def fake_live_smoke(provider, api_key, timeout_seconds):
        captured.update(
            provider=provider.provider,
            model=provider.model_id,
            key=api_key,
            timeout=timeout_seconds,
        )
        return {"provider": provider.provider, "model": provider.model_id, "success": True, "mode": "live"}

    monkeypatch.setattr(runner_main, "run_live_smoke", fake_live_smoke, raising=False)
    exit_code = runner_main.run(
        [
            "live-smoke",
            "--provider",
            "glm",
            "--output",
            str(output),
            "--timeout",
            "15",
        ]
    )
    assert exit_code == 0
    assert captured == {"provider": "glm", "model": "glm-5.2", "key": secret, "timeout": 15}
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "provider": "glm",
        "model": "glm-5.2",
        "success": True,
        "mode": "live",
    }
    assert secret not in output.read_text(encoding="utf-8")


def test_live_smoke_missing_key_preserves_failure_evidence(tmp_path, monkeypatch):
    """A preflight failure must remain auditable instead of disappearing into stderr."""
    monkeypatch.delenv("ZHIPUAI_API_KEY", raising=False)
    output = tmp_path / "missing-key.jsonl"
    exit_code = runner_main.run(
        ["live-smoke", "--provider", "glm", "--output", str(output)]
    )
    assert exit_code == 2
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["success"] is False
    assert record["mode"] == "live"
    assert record["provider"] == "glm"
    assert record["requested_model"] == "glm-5.2"
    assert record["api_key_source"] == "env:ZHIPUAI_API_KEY"
    assert record["error_category"] == "api_key_missing"


def test_reserve_output_command_creates_a_new_run_directory(tmp_path, capsys):
    """Removing the formal CLI wiring must make output reservation unavailable."""
    output_root = tmp_path / "runs"

    exit_code = runner_main.run(
        ["reserve-output", "--output-root", str(output_root), "--run-id", "run-001"]
    )

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report == {
        "created": True,
        "output_directory": str(output_root / "run-001"),
        "run_id": "run-001",
    }
    assert (output_root / "run-001").is_dir()


def test_reserve_output_command_reports_a_collision_without_overwriting(tmp_path, capsys):
    """Letting OutputGuardError escape would remove the CLI's stable failure contract."""
    target = tmp_path / "runs" / "run-001"
    target.mkdir(parents=True)
    marker = target / "historical.txt"
    marker.write_text("keep\n", encoding="utf-8")

    exit_code = runner_main.run(
        ["reserve-output", "--output-root", str(tmp_path / "runs"), "--run-id", "run-001"]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "[output_exists]" in captured.err
    assert marker.read_text(encoding="utf-8") == "keep\n"


def test_generate_fixture_cli_and_verify_cli_complete_offline(tmp_path):
    """Removing either public command must break the promised offline end-to-end flow."""
    output = tmp_path / "run-001"
    generated = subprocess.run(
        [
            sys.executable,
            str(MAIN),
            "generate",
            "--topic",
            "Agent context engineering",
            "--provider",
            "glm",
            "--model",
            "glm-fixture",
            "--seed",
            "42",
            "--output",
            str(output),
            "--mode",
            "fixture",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        shell=False,
    )
    assert generated.returncode == 0, generated.stderr
    assert json.loads(generated.stdout)["valid"] is True

    verified = subprocess.run(
        [sys.executable, str(MAIN), "verify", "--run", str(output)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        shell=False,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["valid"] is True


def test_generate_fixture_cli_refuses_an_existing_output(tmp_path, capsys):
    """A CLI refactor must not bypass the exclusive output guard."""
    output = tmp_path / "run-001"
    output.mkdir()
    marker = output / "historical.txt"
    marker.write_text("keep\n", encoding="utf-8")

    exit_code = runner_main.run(
        [
            "generate",
            "--topic",
            "Agent context engineering",
            "--provider",
            "glm",
            "--model",
            "glm-fixture",
            "--seed",
            "42",
            "--output",
            str(output),
            "--mode",
            "fixture",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "[output_exists]" in captured.err
    assert marker.read_text(encoding="utf-8") == "keep\n"


def test_verify_cli_rejects_a_missing_artifact(tmp_path):
    """The public verifier must expose tampering through its exit code and report."""
    output = tmp_path / "run-001"
    generated = subprocess.run(
        [
            sys.executable,
            str(MAIN),
            "generate",
            "--topic",
            "Agent context engineering",
            "--provider",
            "glm",
            "--model",
            "glm-fixture",
            "--seed",
            "42",
            "--output",
            str(output),
            "--mode",
            "fixture",
        ],
        text=True,
        capture_output=True,
        shell=False,
    )
    assert generated.returncode == 0, generated.stderr
    (output / "results.json").unlink()

    verified = subprocess.run(
        [sys.executable, str(MAIN), "verify", "--run", str(output)],
        text=True,
        capture_output=True,
        shell=False,
    )

    assert verified.returncode == 2
    report = json.loads(verified.stdout)
    assert report["valid"] is False
    assert "artifact_missing" in {error["code"] for error in report["errors"]}


def test_generate_live_cli_fails_without_calling_the_smoke_client(tmp_path, monkeypatch, capsys):
    """Live generation without JiuwenSwarm must fail before any legacy network client is used."""
    def fail_if_called(*args, **kwargs):
        raise AssertionError("live smoke client must not be called by generate")

    monkeypatch.setattr(runner_main, "run_live_smoke", fail_if_called)
    output = tmp_path / "run-001"

    exit_code = runner_main.run(
        [
            "generate",
            "--topic",
            "Agent context engineering",
            "--provider",
            "glm",
            "--model",
            "glm-5.2",
            "--seed",
            "42",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "[generation_backend_unavailable]" in captured.err
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert not (output / "results.json").exists()


def test_verify_cli_returns_system_error_for_a_non_directory_run(tmp_path, capsys):
    """A filesystem target error must remain distinct from a contract rejection."""
    run_path = tmp_path / "not-a-directory"
    run_path.write_text("file\n", encoding="utf-8")

    exit_code = runner_main.run(["verify", "--run", str(run_path)])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "[run_unreadable]" in captured.err
    assert captured.out == ""
