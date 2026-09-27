from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[5]
PACKAGE_ROOT = PROJECT_ROOT / "jiuwenswarm"


class InvokeInputs:
    def __init__(self, conversation_id: str = "") -> None:
        self.conversation_id = conversation_id


class ModelCallInputs:
    def __init__(self, response: object = None) -> None:
        self.response = response


class ToolCallInputs:
    def __init__(
        self,
        *,
        tool_call: object,
        tool_name: str,
        tool_args: object,
        tool_result: object,
        tool_msg: object = None,
    ) -> None:
        self.tool_call = tool_call
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.tool_result = tool_result
        self.tool_msg = tool_msg


class DeepAgentRail:
    def __init__(self) -> None:
        pass


class _Logger:
    def debug(self, *args, **kwargs) -> None:
        pass

    def warning(self, *args, **kwargs) -> None:
        pass


def _package(name: str, path: Path | None = None) -> ModuleType:
    module = ModuleType(name)
    module.__path__ = [] if path is None else [str(path)]
    sys.modules[name] = module
    return module


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _install_runtime_contract() -> None:
    for name in (
        "openjiuwen",
        "openjiuwen.core",
        "openjiuwen.core.single_agent",
        "openjiuwen.core.single_agent.rail",
        "openjiuwen.harness",
        "openjiuwen.harness.rails",
    ):
        _package(name)

    callback = ModuleType("openjiuwen.core.single_agent.rail.base")
    callback.AgentCallbackContext = object
    callback.InvokeInputs = InvokeInputs
    callback.ModelCallInputs = ModelCallInputs
    callback.ToolCallInputs = ToolCallInputs
    sys.modules[callback.__name__] = callback

    rail_base = ModuleType("openjiuwen.harness.rails.base")
    rail_base.DeepAgentRail = DeepAgentRail
    sys.modules[rail_base.__name__] = rail_base

    _package("jiuwenswarm", PACKAGE_ROOT)
    _package("jiuwenswarm.common", PACKAGE_ROOT / "common")
    utils = ModuleType("jiuwenswarm.common.utils")
    utils.logger = _Logger()
    sys.modules[utils.__name__] = utils
    _package("jiuwenswarm.agents", PACKAGE_ROOT / "agents")
    _package("jiuwenswarm.agents.harness", PACKAGE_ROOT / "agents" / "harness")
    _package(
        "jiuwenswarm.agents.harness.common",
        PACKAGE_ROOT / "agents" / "harness" / "common",
    )
    _package(
        "jiuwenswarm.agents.harness.common.rails",
        PACKAGE_ROOT / "agents" / "harness" / "common" / "rails",
    )
    guard_path = PACKAGE_ROOT / "agents" / "harness" / "common" / "rails" / "execution_guard"
    _package("jiuwenswarm.agents.harness.common.rails.execution_guard", guard_path)

    _load(
        "jiuwenswarm.common.execution_evidence",
        PACKAGE_ROOT / "common" / "execution_evidence.py",
    )
    _load(
        "jiuwenswarm.agents.harness.common.rails.execution_guard.circuit_breaker_rail",
        guard_path / "circuit_breaker_rail.py",
    )


_install_runtime_contract()
RAIL_MODULE = _load(
    "jiuwenswarm.agents.harness.common.rails.execution_guard.execution_evidence_rail",
    PACKAGE_ROOT
    / "agents"
    / "harness"
    / "common"
    / "rails"
    / "execution_guard"
    / "execution_evidence_rail.py",
)
ExecutionEvidenceRail = RAIL_MODULE.ExecutionEvidenceRail


@dataclass
class Response:
    content: object


class FakeContext:
    def __init__(
        self,
        inputs: object,
        extra: dict[str, object],
        *,
        exception: Exception | None = None,
    ) -> None:
        self.inputs = inputs
        self.extra = extra
        self.exception = exception
        self.session = None
        self.forced: dict[str, object] | None = None

    def request_force_finish(self, value: dict[str, object]) -> None:
        self.forced = value


def invoke_ctx(conversation_id: str, extra: dict[str, object]) -> FakeContext:
    return FakeContext(InvokeInputs(conversation_id), extra)


def tool_ctx(
    call_id: str,
    result: object,
    extra: dict[str, object],
    *,
    exception: Exception | None = None,
    arguments: dict[str, object] | None = None,
) -> FakeContext:
    args = arguments or {"command": "build command"}
    call = SimpleNamespace(id=call_id, name="command", arguments=args)
    inputs = ToolCallInputs(
        tool_call=call,
        tool_name="command",
        tool_args=args,
        tool_result=result,
    )
    return FakeContext(inputs, extra, exception=exception)


def model_ctx(text: object, extra: dict[str, object]) -> FakeContext:
    return FakeContext(ModelCallInputs(Response(text)), extra)


class ExecutionEvidenceRailTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_tool_claim_requests_force_finish(self) -> None:
        rail = ExecutionEvidenceRail()
        extra: dict[str, object] = {}
        await rail.before_invoke(invoke_ctx("conv-1", extra))
        await rail.after_tool_call(tool_ctx("call-1", {"success": False}, extra))
        ctx = model_ctx("[op:call-1] We completed the build command.", extra)

        await rail.after_model_call(ctx)

        self.assertIsNotNone(ctx.forced)
        assert ctx.forced is not None
        self.assertEqual(ctx.forced["result_type"], "answer")
        audit = extra[rail.AUDIT_KEY]
        assert isinstance(audit, dict)
        self.assertEqual(audit["final_status"], "rejected")
        self.assertEqual(audit["decisions"][0]["evidence_event_ids"], ("conv-1-0001-call-1",))

    async def test_successful_tool_claim_passes_without_force_finish(self) -> None:
        rail = ExecutionEvidenceRail()
        extra: dict[str, object] = {}
        await rail.before_invoke(invoke_ctx("conv-2", extra))
        await rail.after_tool_call(tool_ctx("call-2", {"success": True}, extra))
        ctx = model_ctx("[op:call-2] We completed the build command.", extra)

        await rail.after_model_call(ctx)

        self.assertIsNone(ctx.forced)
        audit = extra[rail.AUDIT_KEY]
        assert isinstance(audit, dict)
        self.assertEqual(audit["final_status"], "accepted")

    async def test_no_claim_is_na_and_does_not_force_finish(self) -> None:
        rail = ExecutionEvidenceRail()
        extra: dict[str, object] = {}
        await rail.before_invoke(invoke_ctx("conv-3", extra))
        ctx = model_ctx("The command failed and remains incomplete.", extra)

        await rail.after_model_call(ctx)

        self.assertIsNone(ctx.forced)
        audit = extra[rail.AUDIT_KEY]
        assert isinstance(audit, dict)
        self.assertEqual(audit["final_status"], "not_applicable")

    async def test_permission_exception_is_recorded_as_denied(self) -> None:
        rail = ExecutionEvidenceRail()
        extra: dict[str, object] = {}
        await rail.before_invoke(invoke_ctx("conv-denied", extra))
        await rail.after_tool_call(
            tool_ctx(
                "restricted",
                None,
                extra,
                exception=PermissionError("permission denied"),
            )
        )
        ctx = model_ctx("[op:restricted] We executed the build command.", extra)

        await rail.after_model_call(ctx)

        audit = extra[rail.AUDIT_KEY]
        assert isinstance(audit, dict)
        self.assertEqual(audit["decisions"][0]["reason"], "matching_event_denied")

    async def test_unstructured_result_is_indeterminate_and_rejected(self) -> None:
        rail = ExecutionEvidenceRail()
        extra: dict[str, object] = {}
        await rail.before_invoke(invoke_ctx("conv-unknown", extra))
        await rail.after_tool_call(tool_ctx("unknown", "opaque output", extra))
        ctx = model_ctx("[op:unknown] We executed the build command.", extra)

        await rail.after_model_call(ctx)

        audit = extra[rail.AUDIT_KEY]
        assert isinstance(audit, dict)
        self.assertEqual(audit["decisions"][0]["status"], "indeterminate")

    async def test_response_content_blocks_are_joined(self) -> None:
        rail = ExecutionEvidenceRail()
        extra: dict[str, object] = {}
        await rail.before_invoke(invoke_ctx("conv-blocks", extra))
        await rail.after_tool_call(tool_ctx("blocks", {"success": True}, extra))
        ctx = model_ctx(
            [{"type": "text", "text": "[op:blocks] We completed the build command."}],
            extra,
        )

        await rail.after_model_call(ctx)

        self.assertIsNone(ctx.forced)
        audit = extra[rail.AUDIT_KEY]
        assert isinstance(audit, dict)
        self.assertEqual(audit["raw_output"], "[op:blocks] We completed the build command.")

    async def test_after_invoke_cleans_only_its_session(self) -> None:
        rail = ExecutionEvidenceRail()
        extra_a: dict[str, object] = {}
        extra_b: dict[str, object] = {}
        await rail.before_invoke(invoke_ctx("conv-a", extra_a))
        await rail.before_invoke(invoke_ctx("conv-b", extra_b))
        await rail.after_tool_call(tool_ctx("a", {"success": True}, extra_a))
        await rail.after_tool_call(tool_ctx("b", {"success": True}, extra_b))

        await rail.after_invoke(invoke_ctx("conv-a", extra_a))

        self.assertNotIn("conv-a", rail._events)
        self.assertIn("conv-b", rail._events)


if __name__ == "__main__":
    unittest.main()
