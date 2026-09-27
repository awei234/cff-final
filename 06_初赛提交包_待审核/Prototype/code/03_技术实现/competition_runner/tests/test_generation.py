from __future__ import annotations

import json

import pytest

from competition_runner.artifact_contract import REQUIRED_ARTIFACTS
from competition_runner.generation import (
    FixtureBackend,
    GenerationError,
    GenerationRequest,
    generate_run,
)
from competition_runner.output_guard import OutputGuardError
from competition_runner.verification import verify_run


def _request_for(output, *, mode="fixture"):
    return GenerationRequest(
        topic="Agent context engineering",
        provider="glm",
        model="glm-fixture",
        seed=42,
        mode=mode,
        output=output,
        source_commit="a" * 40,
    )


def test_fixture_generation_creates_a_verified_nine_artifact_run(tmp_path):
    """Skipping any generation stage must prevent a fixture run from proving completeness."""
    output = tmp_path / "run-001"

    report = generate_run(_request_for(output), backend=FixtureBackend())

    assert report["valid"] is True
    assert {path.name for path in output.iterdir()} == set(REQUIRED_ARTIFACTS)
    assert verify_run(output).valid is True
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "fixture"
    assert manifest["status"] == "completed"
    resource = json.loads((output / "resource.json").read_text(encoding="utf-8"))
    assert resource["measurement_status"] == "not_applicable"
    assert resource["token_usage"] is None
    assert resource["duration_seconds"] is None
    assert resource["cost"] is None


def test_generate_run_refuses_an_existing_output(tmp_path):
    """Replacing exclusive creation must never overwrite historical evidence."""
    output = tmp_path / "run-001"
    output.mkdir()
    marker = output / "historical.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(OutputGuardError) as exc:
        generate_run(_request_for(output), backend=FixtureBackend())

    assert exc.value.code == "output_exists"
    assert marker.read_text(encoding="utf-8") == "keep"


class _FailingBackend:
    def generate(self, request, run_id):
        raise GenerationError("synthetic_failure", "synthetic backend failure")


def test_generate_run_preserves_a_failed_manifest(tmp_path):
    """Deleting a partial run would erase the evidence needed to audit a failure."""
    output = tmp_path / "run-001"

    with pytest.raises(GenerationError) as exc:
        generate_run(_request_for(output), backend=_FailingBackend())

    assert exc.value.code == "synthetic_failure"
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["failure_code"] == "synthetic_failure"


def test_live_mode_rejects_the_fixture_backend_without_fabricating_results(tmp_path):
    """Passing the offline backend must not let live mode impersonate a real provider run."""
    output = tmp_path / "run-001"

    with pytest.raises(GenerationError) as exc:
        generate_run(_request_for(output, mode="live"), backend=FixtureBackend())

    assert exc.value.code == "generation_backend_unavailable"
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["failure_code"] == "generation_backend_unavailable"
    assert not (output / "results.json").exists()
    assert not (output / "paper.tex").exists()
    assert not (output / "paper.pdf").exists()
