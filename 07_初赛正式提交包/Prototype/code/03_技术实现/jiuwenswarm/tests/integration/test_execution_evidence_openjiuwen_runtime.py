from __future__ import annotations

from types import SimpleNamespace
import unittest
from uuid import uuid4

from openjiuwen.core.single_agent.agent_callback_manager import AgentCallbackManager
from openjiuwen.core.single_agent.rail.base import (
    AgentCallbackContext,
    AgentCallbackEvent,
    InvokeInputs,
    ModelCallInputs,
    ToolCallInputs,
)
from openjiuwen.harness.rails.base import DeepAgentRail

from jiuwenswarm.agents.harness.common.rails.execution_guard.execution_evidence_rail import (
    ExecutionEvidenceRail,
)


class _NativeAgent:
    def __init__(self) -> None:
        namespace = f"s2-02-{uuid4()}"
        self.agent_callback_manager = AgentCallbackManager(
            namespace,
            event_namespace=namespace,
        )


class OpenJiuwenExecutionEvidenceRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.agent = _NativeAgent()
        self.rail = ExecutionEvidenceRail()
        self.assertIsInstance(self.rail, DeepAgentRail)
        await self.agent.agent_callback_manager.register_rail(self.rail, self.agent)
        self.extra: dict[str, object] = {}

    async def asyncTearDown(self) -> None:
        await self.agent.agent_callback_manager.clear()

    def _ctx(self, inputs: object, *, exception: Exception | None = None) -> AgentCallbackContext:
        return AgentCallbackContext(
            agent=self.agent,
            inputs=inputs,
            extra=self.extra,
            exception=exception,
        )

    async def _run_scenario(
        self,
        *,
        scenario_id: str,
        text: str,
        tools: list[dict[str, object]],
    ) -> tuple[dict[str, object], bool]:
        invoke_ctx = self._ctx(
            InvokeInputs(query="validate evidence", conversation_id=scenario_id)
        )
        await invoke_ctx.fire(AgentCallbackEvent.BEFORE_INVOKE)

        for item in tools:
            operation_id = str(item["operation_id"])
            tool_name = str(item.get("tool_name", "command"))
            arguments = item.get("arguments", {"command": "build command"})
            tool_call = SimpleNamespace(
                id=operation_id,
                name=tool_name,
                arguments=arguments,
            )
            exception = item.get("exception")
            tool_ctx = self._ctx(
                ToolCallInputs(
                    tool_call=tool_call,
                    tool_name=tool_name,
                    tool_args=arguments,
                    tool_result=item.get("result"),
                ),
                exception=exception if isinstance(exception, Exception) else None,
            )
            event = (
                AgentCallbackEvent.ON_TOOL_EXCEPTION
                if exception is not None
                else AgentCallbackEvent.AFTER_TOOL_CALL
            )
            await tool_ctx.fire(event)

        model_ctx = self._ctx(ModelCallInputs(response={"content": text}))
        await model_ctx.fire(AgentCallbackEvent.AFTER_MODEL_CALL)
        audit = dict(self.extra[self.rail.AUDIT_KEY])
        forced = model_ctx.has_force_finish_request
        await invoke_ctx.fire(AgentCallbackEvent.AFTER_INVOKE)
        return audit, forced

    async def test_native_tool_exception_is_recorded_as_denied_evidence(self) -> None:
        invoke_ctx = self._ctx(InvokeInputs(query="build", conversation_id="native-denied"))
        await invoke_ctx.fire(AgentCallbackEvent.BEFORE_INVOKE)

        tool_call = SimpleNamespace(
            id="denied-op",
            name="command",
            arguments={"command": "build command"},
        )
        exception_ctx = self._ctx(
            ToolCallInputs(
                tool_call=tool_call,
                tool_name="command",
                tool_args=tool_call.arguments,
                tool_result=None,
            ),
            exception=PermissionError("permission denied"),
        )
        await exception_ctx.fire(AgentCallbackEvent.ON_TOOL_EXCEPTION)

        model_ctx = self._ctx(
            ModelCallInputs(
                response={"content": "[op:denied-op] We completed the build command."}
            )
        )
        await model_ctx.fire(AgentCallbackEvent.AFTER_MODEL_CALL)

        audit = self.extra[self.rail.AUDIT_KEY]
        self.assertEqual(
            [event["status"] for event in audit["events"]],
            ["denied"],
        )
        self.assertEqual(audit["decisions"][0]["reason"], "matching_event_denied")
        force_finish = model_ctx.consume_force_finish()
        self.assertIsNotNone(force_finish)

    async def test_native_callback_chain_enforces_the_eight_scenario_matrix(self) -> None:
        cases = [
            {
                "id": "native-success",
                "text": "[op:build_ok] We completed the build command.",
                "tools": [
                    {"operation_id": "build_ok", "result": {"status": "success", "exit_code": 0}}
                ],
                "status": "accepted",
                "reason": "matching_successful_evidence",
                "forced": False,
            },
            {
                "id": "native-failed",
                "text": "[op:build_failed] We completed the build command.",
                "tools": [
                    {"operation_id": "build_failed", "result": {"status": "failed", "exit_code": 7}}
                ],
                "status": "rejected",
                "reason": "matching_event_failed",
                "forced": True,
            },
            {
                "id": "native-denied",
                "text": "[op:restricted] We executed the restricted evaluator.",
                "tools": [
                    {"operation_id": "restricted", "exception": PermissionError("permission denied")}
                ],
                "status": "rejected",
                "reason": "matching_event_denied",
                "forced": True,
            },
            {
                "id": "native-missing",
                "text": "[op:missing] We opened the missing artifact.",
                "tools": [
                    {
                        "operation_id": "missing",
                        "tool_name": "read_file",
                        "arguments": {"path": "missing artifact"},
                        "exception": FileNotFoundError("missing artifact"),
                    }
                ],
                "status": "rejected",
                "reason": "matching_event_failed",
                "forced": True,
            },
            {
                "id": "native-unavailable",
                "text": "[op:remote] We queried the remote service.",
                "tools": [
                    {
                        "operation_id": "remote",
                        "tool_name": "query",
                        "arguments": {"query": "remote service"},
                        "exception": ConnectionError("service unavailable"),
                    }
                ],
                "status": "rejected",
                "reason": "matching_event_unavailable",
                "forced": True,
            },
            {
                "id": "native-mixed",
                "text": "All requested operations were completed.",
                "tools": [
                    {"operation_id": "mixed_ok", "result": {"status": "success", "exit_code": 0}},
                    {"operation_id": "mixed_failed", "result": {"status": "failed", "exit_code": 1}},
                ],
                "status": "rejected",
                "reason": "aggregate_contains_unsuccessful_events",
                "forced": True,
            },
            {
                "id": "native-indeterminate",
                "text": "We completed the deployment.",
                "tools": [
                    {"operation_id": "deploy_east", "result": {"status": "success", "exit_code": 0}},
                    {"operation_id": "deploy_west", "result": {"status": "success", "exit_code": 0}},
                ],
                "status": "rejected",
                "reason": "claim_has_no_operation_id",
                "forced": True,
            },
            {
                "id": "native-not-applicable",
                "text": "The command failed and remains incomplete; no completion is claimed.",
                "tools": [],
                "status": "not_applicable",
                "reason": None,
                "forced": False,
            },
        ]

        for case in cases:
            with self.subTest(case=case["id"]):
                self.extra = {}
                audit, forced = await self._run_scenario(
                    scenario_id=str(case["id"]),
                    text=str(case["text"]),
                    tools=case["tools"],
                )
                decisions = audit["decisions"]
                reason = decisions[0]["reason"] if decisions else None
                self.assertEqual(audit["final_status"], case["status"])
                self.assertEqual(reason, case["reason"])
                self.assertEqual(forced, case["forced"])


if __name__ == "__main__":
    unittest.main()
