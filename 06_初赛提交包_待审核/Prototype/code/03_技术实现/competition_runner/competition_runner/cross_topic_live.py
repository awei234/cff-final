"""Authorized, provider-isolated live execution for one frozen S4 task."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from .cross_topic import REQUIRED_ARTIFACTS, validate_cross_topic_protocol
from .output_guard import reserve_output_directory
from .paper_pdf import PaperPdfError, derive_paper_pdf


CONTENT_ARTIFACTS = (
    "prompt.txt",
    "tool_trace.jsonl",
    "results.json",
    "paper.tex",
    "paper.pdf",
    "resource.json",
    "research_materials.json",
    "plan.json",
    "execution_report.json",
    "rail_events.jsonl",
    "human_interventions.jsonl",
)
MAX_PROVIDER_RESPONSE_BYTES = 65536


def _json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


class CrossTopicLiveError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CrossTopicLiveError("evidence_unreadable", f"unable to read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CrossTopicLiveError("evidence_invalid", f"JSON must be an object: {path}")
    return value


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest().upper()


def _write_bytes_atomic(path: Path, value: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(value)
    temporary.replace(path)


def _write_text_atomic(path: Path, value: str) -> None:
    _write_bytes_atomic(path, value.encode("utf-8"))


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    _write_text_atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _write_jsonl_atomic(path: Path, values: list[dict[str, Any]]) -> None:
    if not values:
        raise CrossTopicLiveError("bundle_invalid", f"{path.name} must not be empty")
    _write_text_atomic(
        path,
        "".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values),
    )


def _require_objects(value: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or not all(isinstance(item, dict) for item in value):
        raise CrossTopicLiveError("bundle_invalid", f"{name} must be a non-empty object list")
    return value


def _validate_bundle(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CrossTopicLiveError("bundle_invalid", "provider response must be a JSON object")
    value = dict(value)
    resource = value.get("resource")
    if isinstance(resource, str):
        if not resource.strip():
            raise CrossTopicLiveError("bundle_invalid", "resource must be an object")
        try:
            parsed_resource = json.loads(resource)
        except json.JSONDecodeError:
            parsed_resource = None
        value["resource"] = (
            parsed_resource
            if isinstance(parsed_resource, dict)
            else {"raw_text": resource, "normalized_from": "string"}
        )
    object_fields = ("results", "resource", "research_materials", "plan", "execution_report")
    for name in object_fields:
        if not isinstance(value.get(name), dict):
            raise CrossTopicLiveError("bundle_invalid", f"{name} must be an object")
    paper_tex = value.get("paper_tex")
    if not isinstance(paper_tex, str) or not paper_tex.strip():
        raise CrossTopicLiveError("bundle_invalid", "paper_tex must be non-empty text")
    try:
        value["paper_pdf"] = derive_paper_pdf(paper_tex)
    except PaperPdfError as exc:
        raise CrossTopicLiveError("bundle_invalid", str(exc)) from exc
    for name in ("tool_events", "rail_events", "human_interventions"):
        value[name] = _require_objects(value.get(name), name)
    return value


def prepare_cross_topic_live_task(
    *,
    protocol_path: Path,
    provider_config_path: Path,
    output_root: Path,
    task_id: str,
    confirmed: bool,
    max_calls: int,
    environ: Mapping[str, str],
    allow_deepseek_demo: bool = False,
) -> dict[str, Any]:
    """Validate one frozen task and its authorization before exposing a credential."""
    if not confirmed:
        raise CrossTopicLiveError("live_confirmation_required", "explicit live confirmation is required")
    if isinstance(max_calls, bool) or not isinstance(max_calls, int) or max_calls <= 0:
        raise CrossTopicLiveError("call_limit_invalid", "max_calls must be a positive integer")
    protocol = _read_json(protocol_path)
    providers = _read_json(provider_config_path)
    provider_hash = _sha256_file(provider_config_path)
    if protocol.get("provider_config_sha256") != provider_hash:
        raise CrossTopicLiveError("provider_config_drift", "provider configuration changed after freeze")
    task = next(
        (item for item in protocol.get("tasks", []) if isinstance(item, dict) and item.get("task_id") == task_id),
        None,
    )
    if task is None:
        raise CrossTopicLiveError("task_unknown", f"unknown frozen task: {task_id}")
    is_deepseek = task.get("provider") == "deepseek"
    if is_deepseek and not allow_deepseek_demo:
        raise CrossTopicLiveError("task_blocked_budget", "DeepSeek remains blocked for budget; pass the explicit demo override")
    if task.get("status") == "blocked_budget" and not (is_deepseek and allow_deepseek_demo):
        raise CrossTopicLiveError("task_blocked_budget", "selected task is blocked by the frozen budget policy")
    if is_deepseek and allow_deepseek_demo:
        if task.get("task_id") != "context-engineering-deepseek-seed42":
            raise CrossTopicLiveError("demo_task_invalid", "the DeepSeek demo is fixed to the context-engineering task")
        if max_calls > 3:
            raise CrossTopicLiveError("demo_call_limit_invalid", "DeepSeek demo max_calls must be between 1 and 3")
    output_relpath = task.get("output_relpath")
    if not isinstance(output_relpath, str):
        raise CrossTopicLiveError("protocol_invalid", "selected output path is invalid")
    validation = validate_cross_topic_protocol(
        protocol,
        output_root=output_root,
        selected_output_relpaths={output_relpath},
    )
    if not validation["valid"]:
        code = "formal_output_exists" if "cross_topic_output_exists" in validation["errors"] else "protocol_invalid"
        raise CrossTopicLiveError(code, f"cross-topic validation failed: {validation['errors']}")
    provider_name = str(task["provider"])
    provider = providers.get(provider_name)
    if not isinstance(provider, dict):
        raise CrossTopicLiveError("provider_invalid", f"provider missing: {provider_name}")
    if provider.get("model_id") != task.get("model_id") or provider.get("api_key_env") != task.get("api_key_env"):
        raise CrossTopicLiveError("provider_task_mismatch", "selected provider no longer matches the task")
    key_name = str(provider["api_key_env"])
    key_present = bool(environ.get(key_name, "").strip())
    request = {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol["protocol_sha256"],
        "task": dict(task),
        "prompt": str(protocol["prompt_template"]).format(topic=task["topic"]),
        "required_artifacts": list(protocol["required_artifacts"]),
    }
    return {
        "task": dict(task),
        "request": request,
        "provider": {
            "api_base": provider["api_base"],
            "model_id": provider["model_id"],
            "api_key_env": key_name,
            "api_key_present": key_present,
        },
        "sensitive_env_names": sorted(
            str(item["api_key_env"])
            for item in providers.values()
            if isinstance(item, dict) and "api_key_env" in item
        ),
        "authorized_call_limit": max_calls,
        "demo_override": bool(is_deepseek and allow_deepseek_demo),
        "output_path": output_root / output_relpath,
    }


class ProviderCommandCrossTopicBackend:
    """Invoke a cross-topic pipeline command with one isolated provider credential."""

    def __init__(
        self,
        *,
        command: Sequence[str],
        prepared: dict[str, Any],
        environ: Mapping[str, str],
        timeout_seconds: float = 600,
    ) -> None:
        if not command:
            raise CrossTopicLiveError("provider_command_invalid", "provider command must not be empty")
        provider = prepared["provider"]
        key = environ.get(provider["api_key_env"], "").strip()
        if not key:
            raise CrossTopicLiveError("api_key_missing", f"missing environment variable: {provider['api_key_env']}")
        self.command = list(command)
        self.prepared = prepared
        self._source_environ = dict(environ)
        self._api_key = key
        self.timeout_seconds = timeout_seconds
        self.calls_made = 0
        self.response_diagnostics: dict[str, Any] | None = None
        self._secrets = {
            value
            for name in prepared["sensitive_env_names"]
            if (value := environ.get(name, "").strip())
        }

    def _capture_response(self, stdout: str) -> None:
        raw = stdout.encode("utf-8")
        redacted = stdout
        for secret in sorted(self._secrets, key=len, reverse=True):
            redacted = redacted.replace(secret, "[REDACTED]")
        redacted_bytes = redacted.encode("utf-8")
        clipped = redacted_bytes[:MAX_PROVIDER_RESPONSE_BYTES]
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = None
        field_types = (
            {name: _json_type_name(value) for name, value in sorted(parsed.items())}
            if isinstance(parsed, dict) else {}
        )
        self.response_diagnostics = {
            "provider_response_sha256": sha256(raw).hexdigest().upper(),
            "provider_response_bytes": len(raw),
            "provider_response_truncated": len(raw) > MAX_PROVIDER_RESPONSE_BYTES,
            "provider_response_field_types": field_types,
            "provider_response_text": clipped.decode("utf-8", errors="replace"),
        }

    def generate(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.calls_made >= self.prepared["authorized_call_limit"]:
            raise CrossTopicLiveError("call_limit_exceeded", "authorized provider call limit reached")
        provider = self.prepared["provider"]
        env = os.environ.copy()
        env.update(self._source_environ)
        for name in self.prepared["sensitive_env_names"]:
            env.pop(name, None)
        env.update(
            {
                "OPENAI_COMPAT_API_BASE": str(provider["api_base"]),
                "OPENAI_COMPAT_API_KEY": self._api_key,
                "OPENAI_COMPAT_MODEL": str(provider["model_id"]),
                "CROSS_TOPIC_SEED": str(self.prepared["task"]["seed"]),
                "CROSS_TOPIC_CALL_LIMIT": str(self.prepared["authorized_call_limit"]),
            }
        )
        self.calls_made += 1
        try:
            completed = subprocess.run(
                self.command,
                input=json.dumps(request, ensure_ascii=False),
                text=True,
                capture_output=True,
                shell=False,
                timeout=self.timeout_seconds,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CrossTopicLiveError("provider_command_failed", "provider command could not complete") from exc
        self._capture_response(completed.stdout)
        if completed.returncode != 0:
            raise CrossTopicLiveError(
                "provider_command_failed",
                f"provider command exited with code {completed.returncode}",
            )
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise CrossTopicLiveError("bundle_invalid", "provider command returned invalid JSON") from exc
        return _validate_bundle(value)


def verify_cross_topic_run(
    output: Path,
    *,
    expected_task: dict[str, Any],
    require_stored_report: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    expected_names = set(REQUIRED_ARTIFACTS)
    if not require_stored_report:
        expected_names.remove("verification_report.json")
    actual_names = {item.name for item in output.iterdir() if item.is_file()} if output.is_dir() else set()
    if actual_names != expected_names:
        errors.append("artifact_set_invalid")
    try:
        manifest = _read_json(output / "run_manifest.json")
        provenance = _read_json(output / "provenance.json")
    except CrossTopicLiveError:
        manifest = {}
        provenance = {}
        errors.append("json_invalid")
    if manifest.get("task_id") != expected_task.get("task_id") or manifest.get("input_sha256") != expected_task.get("input_sha256"):
        errors.append("task_identity_mismatch")
    if manifest.get("status") != "completed":
        errors.append("run_incomplete")
    derivation = provenance.get("pdf_derivation")
    try:
        paper_tex_hash = _sha256_file(output / "paper.tex")
    except OSError:
        paper_tex_hash = None
    if derivation != {
        "method": "stdlib-latex-text-pdf-v1",
        "paper_tex_sha256": paper_tex_hash,
    }:
        errors.append("pdf_derivation_invalid")
    for name in ("results.json", "resource.json", "research_materials.json", "plan.json", "execution_report.json"):
        try:
            _read_json(output / name)
        except CrossTopicLiveError:
            errors.append(f"{name}:invalid")
    for name in ("tool_trace.jsonl", "rail_events.jsonl", "human_interventions.jsonl"):
        try:
            lines = (output / name).read_text(encoding="utf-8").splitlines()
            if not lines or not all(isinstance(json.loads(line), dict) for line in lines):
                raise ValueError(name)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            errors.append(f"{name}:invalid")
    try:
        pdf = (output / "paper.pdf").read_bytes()
        if not pdf.startswith(b"%PDF-") or b"%%EOF" not in pdf:
            errors.append("paper.pdf:invalid")
    except OSError:
        errors.append("paper.pdf:invalid")
    hashes = provenance.get("artifact_hashes")
    if not isinstance(hashes, dict):
        errors.append("provenance_hashes_invalid")
    else:
        for name in CONTENT_ARTIFACTS:
            try:
                if hashes.get(name) != _sha256_file(output / name):
                    errors.append(f"{name}:hash_mismatch")
            except OSError:
                errors.append(f"{name}:hash_missing")
    if require_stored_report:
        try:
            stored = _read_json(output / "verification_report.json")
            if stored.get("valid") is not True or stored.get("task_id") != expected_task.get("task_id"):
                errors.append("stored_report_invalid")
        except CrossTopicLiveError:
            errors.append("stored_report_invalid")
    return {
        "schema_version": 1,
        "task_id": expected_task.get("task_id"),
        "valid": not errors,
        "errors": sorted(set(errors)),
        "artifact_count": len(actual_names),
    }


def execute_prepared_cross_topic_task(
    *,
    prepared: dict[str, Any],
    backend: ProviderCommandCrossTopicBackend,
) -> dict[str, Any]:
    task = prepared["task"]
    output_path: Path = prepared["output_path"]
    output = reserve_output_directory(output_path.parent, output_path.name)
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "protocol_id": prepared["request"]["protocol_id"],
        "protocol_sha256": prepared["request"]["protocol_sha256"],
        "task_id": task["task_id"],
        "input_sha256": task["input_sha256"],
        "topic_id": task["topic_id"],
        "topic": task["topic"],
        "provider": task["provider"],
        "model_id": task["model_id"],
        "seed": task["seed"],
        "mode": "live",
        "authorized_call_limit": prepared["authorized_call_limit"],
        "model_api_calls": 0,
        "status": "running",
        "required_artifacts": list(REQUIRED_ARTIFACTS),
    }
    _write_json_atomic(output / "run_manifest.json", manifest)
    try:
        bundle = backend.generate(prepared["request"])
        manifest["model_api_calls"] = backend.calls_made
        _write_text_atomic(output / "prompt.txt", prepared["request"]["prompt"] + "\n")
        _write_jsonl_atomic(output / "tool_trace.jsonl", bundle["tool_events"])
        _write_json_atomic(output / "results.json", bundle["results"])
        _write_text_atomic(output / "paper.tex", bundle["paper_tex"])
        _write_bytes_atomic(output / "paper.pdf", bundle["paper_pdf"])
        _write_json_atomic(output / "resource.json", bundle["resource"])
        _write_json_atomic(output / "research_materials.json", bundle["research_materials"])
        _write_json_atomic(output / "plan.json", bundle["plan"])
        _write_json_atomic(output / "execution_report.json", bundle["execution_report"])
        _write_jsonl_atomic(output / "rail_events.jsonl", bundle["rail_events"])
        _write_jsonl_atomic(output / "human_interventions.jsonl", bundle["human_interventions"])
        provenance = {
            "schema_version": 1,
            "task_id": task["task_id"],
            "input_sha256": task["input_sha256"],
            "source_commit": task["source_commit"],
            "generator": {"name": type(backend).__name__, "mode": "live"},
            "pdf_derivation": {
                "method": "stdlib-latex-text-pdf-v1",
                "paper_tex_sha256": _sha256_file(output / "paper.tex"),
            },
            "artifact_hashes": {name: _sha256_file(output / name) for name in CONTENT_ARTIFACTS},
        }
        _write_json_atomic(output / "provenance.json", provenance)
        manifest["status"] = "completed"
        _write_json_atomic(output / "run_manifest.json", manifest)
        initial = verify_cross_topic_run(output, expected_task=task, require_stored_report=False)
        if not initial["valid"]:
            raise CrossTopicLiveError("artifact_invalid", f"artifact verification failed: {initial['errors']}")
        _write_json_atomic(output / "verification_report.json", initial)
        final = verify_cross_topic_run(output, expected_task=task)
        if not final["valid"]:
            raise CrossTopicLiveError("artifact_invalid", f"stored verification failed: {final['errors']}")
        return final
    except CrossTopicLiveError as exc:
        manifest["status"] = "failed"
        manifest["failure_code"] = exc.code
        manifest["model_api_calls"] = backend.calls_made
        _write_json_atomic(output / "run_manifest.json", manifest)
        if not (output / "execution_report.json").exists():
            failure_report: dict[str, Any] = {
                "schema_version": 1,
                "task_id": task["task_id"],
                "status": "failed",
                "failure_code": exc.code,
                "failure_message": str(exc),
                "model_api_calls": backend.calls_made,
            }
            if backend.response_diagnostics is not None:
                failure_report.update(backend.response_diagnostics)
            _write_json_atomic(output / "execution_report.json", failure_report)
        raise


__all__ = [
    "CrossTopicLiveError",
    "ProviderCommandCrossTopicBackend",
    "execute_prepared_cross_topic_task",
    "prepare_cross_topic_live_task",
    "verify_cross_topic_run",
]
