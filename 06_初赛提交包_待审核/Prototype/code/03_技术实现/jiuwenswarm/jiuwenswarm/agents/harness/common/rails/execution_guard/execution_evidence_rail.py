from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Mapping

from openjiuwen.core.single_agent.rail.base import (
    AgentCallbackContext,
    InvokeInputs,
    ModelCallInputs,
    ToolCallInputs,
)
from openjiuwen.harness.rails.base import DeepAgentRail

from jiuwenswarm.agents.harness.common.rails.execution_guard.circuit_breaker_rail import (
    ToolResultErrorDetector,
)
from jiuwenswarm.common.execution_evidence import (
    ExecutionEvidenceEvent,
    evaluate_completion_claims,
)


class ExecutionEvidenceRail(DeepAgentRail):
    """Reject completion claims that lack matching successful tool evidence."""

    priority = 85
    SID_KEY = "__jiuwenswarm_execution_evidence_session_id__"
    AUDIT_KEY = "__jiuwenswarm_execution_evidence_gate__"

    def __init__(self) -> None:
        super().__init__()
        self._events: dict[str, list[ExecutionEvidenceEvent]] = {}
        self._counters: dict[str, int] = {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _invoke_sid(self, ctx: AgentCallbackContext) -> str:
        conversation_id = getattr(ctx.inputs, "conversation_id", "")
        return str(conversation_id or "default")

    def _resolve_sid(self, ctx: AgentCallbackContext) -> str:
        value = ctx.extra.get(self.SID_KEY)
        return str(value) if value else self._invoke_sid(ctx)

    async def before_invoke(self, ctx: AgentCallbackContext) -> None:
        if not isinstance(ctx.inputs, InvokeInputs):
            return
        sid = self._invoke_sid(ctx)
        ctx.extra[self.SID_KEY] = sid
        self._events[sid] = []
        self._counters[sid] = 0

    async def after_tool_call(self, ctx: AgentCallbackContext) -> None:
        if not isinstance(ctx.inputs, ToolCallInputs):
            return
        sid = self._resolve_sid(ctx)
        ctx.extra[self.SID_KEY] = sid
        event = self._event_from_tool_ctx(ctx, sid)
        self._events.setdefault(sid, []).append(event)

    async def on_tool_exception(self, ctx: AgentCallbackContext) -> None:
        await self.after_tool_call(ctx)

    async def after_model_call(self, ctx: AgentCallbackContext) -> None:
        if not isinstance(ctx.inputs, ModelCallInputs):
            return
        sid = self._resolve_sid(ctx)
        result = evaluate_completion_claims(
            self._response_text(ctx.inputs.response),
            tuple(self._events.get(sid, ())),
            claimed_at=self._now(),
        )
        audit = result.to_audit_dict()
        audit["events"] = [
            {
                "event_id": event.event_id,
                "operation_id": event.operation_id,
                "tool": event.tool,
                "action": event.action,
                "target": event.target,
                "started_at": event.started_at,
                "finished_at": event.finished_at,
                "status": event.status,
                "detail": event.detail,
                "exit_code": event.exit_code,
            }
            for event in self._events.get(sid, ())
        ]
        ctx.extra[self.AUDIT_KEY] = audit
        if not result.accepted:
            ctx.request_force_finish(
                {
                    "output": result.revision_prompt or "Execution evidence rejected the draft.",
                    "result_type": "answer",
                    "execution_evidence_gate": audit,
                }
            )

    async def after_invoke(self, ctx: AgentCallbackContext) -> None:
        sid = self._resolve_sid(ctx)
        self._events.pop(sid, None)
        self._counters.pop(sid, None)

    def _event_from_tool_ctx(
        self,
        ctx: AgentCallbackContext,
        sid: str,
    ) -> ExecutionEvidenceEvent:
        inputs = ctx.inputs
        tool_call = inputs.tool_call
        tool_name = str(inputs.tool_name or getattr(tool_call, "name", "") or "tool")
        arguments = inputs.tool_args
        if arguments is None:
            arguments = getattr(tool_call, "arguments", None)

        self._counters[sid] = self._counters.get(sid, 0) + 1
        sequence = self._counters[sid]
        call_id = str(getattr(tool_call, "id", "") or "")
        explicit_operation_id = (
            arguments.get("operation_id")
            if isinstance(arguments, dict)
            else None
        )
        operation_id = str(explicit_operation_id or call_id or f"{tool_name}-{sequence:04d}")
        event_id = f"{sid}-{sequence:04d}-{operation_id}"
        timestamp = self._now()
        status, detail, exit_code = self._status_from_tool_ctx(ctx)
        return ExecutionEvidenceEvent(
            event_id=event_id,
            operation_id=operation_id,
            tool=tool_name,
            action=self._infer_action(tool_name),
            target=self._infer_target(arguments, tool_name),
            started_at=timestamp,
            finished_at=timestamp,
            status=status,
            detail=detail,
            exit_code=exit_code,
        )

    @staticmethod
    def _infer_action(tool_name: str) -> str:
        name = tool_name.strip().lower()
        if any(token in name for token in ("query", "search", "lookup")):
            return "query"
        if any(token in name for token in ("read", "open", "inspect", "list")):
            return "inspect"
        if any(token in name for token in ("test", "validate", "verify", "check")):
            return "validate"
        return "execute"

    @staticmethod
    def _infer_target(arguments: Any, tool_name: str) -> str:
        if isinstance(arguments, dict):
            for key in (
                "target",
                "path",
                "file_path",
                "command",
                "query",
                "url",
                "name",
            ):
                value = arguments.get(key)
                if value not in (None, ""):
                    return str(value)
            return json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str)
        if arguments not in (None, ""):
            return str(arguments)
        return tool_name

    @classmethod
    def _status_from_tool_ctx(
        cls,
        ctx: AgentCallbackContext,
    ) -> tuple[str, str, int | None]:
        inputs = ctx.inputs
        result = inputs.tool_result
        detail = cls._result_detail(result, ctx.exception)
        exit_code = cls._exit_code(result)
        lowered = detail.lower()

        if ctx.exception is not None:
            if isinstance(ctx.exception, PermissionError) or cls._looks_denied(lowered):
                return "denied", detail, exit_code
            if cls._looks_unavailable(lowered):
                return "unavailable", detail, exit_code
            return "failed", detail, exit_code

        explicit_status = cls._explicit_status(result)
        if explicit_status in {"success", "failed", "denied", "unavailable", "indeterminate", "not_called"}:
            return explicit_status, detail, exit_code
        if ToolResultErrorDetector.has_explicit_success(result):
            return "success", detail, exit_code
        if exit_code == 0:
            return "success", detail, exit_code
        if ToolResultErrorDetector.has_error(result):
            if cls._looks_denied(lowered):
                return "denied", detail, exit_code
            if cls._looks_unavailable(lowered):
                return "unavailable", detail, exit_code
            return "failed", detail, exit_code
        return "indeterminate", detail, exit_code

    @staticmethod
    def _explicit_status(result: Any) -> str | None:
        if isinstance(result, dict):
            value = result.get("status")
        else:
            value = getattr(result, "status", None)
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        aliases = {"ok": "success", "successful": "success", "error": "failed", "failure": "failed"}
        return aliases.get(normalized, normalized)

    @staticmethod
    def _exit_code(result: Any) -> int | None:
        keys = ("exit_code", "exitCode", "returncode", "return_code")
        if isinstance(result, dict):
            for key in keys:
                value = result.get(key)
                if isinstance(value, int):
                    return value
        else:
            for key in keys:
                value = getattr(result, key, None)
                if isinstance(value, int):
                    return value
        return None

    @staticmethod
    def _looks_denied(text: str) -> bool:
        return any(token in text for token in ("permission denied", "access denied", "forbidden", "not authorized", "拒绝", "无权限"))

    @staticmethod
    def _looks_unavailable(text: str) -> bool:
        return any(
            token in text
            for token in (
                "unavailable",
                "connection refused",
                "connection reset",
                "network is unreachable",
                "timed out",
                "timeout",
                "服务不可用",
                "网络不可用",
            )
        )

    @staticmethod
    def _result_detail(result: Any, exception: Exception | None) -> str:
        if exception is not None:
            return f"{type(exception).__name__}: {exception}"
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, sort_keys=True, default=str)
        model_dump = getattr(result, "model_dump", None)
        if callable(model_dump):
            try:
                return json.dumps(model_dump(), ensure_ascii=False, sort_keys=True, default=str)
            except Exception:
                return str(result)
        return str(result)

    @classmethod
    def _response_text(cls, response: Any) -> str:
        if response is None:
            return ""
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            for key in ("content", "output", "text", "message"):
                if key in response:
                    return cls._content_text(response[key])
            return ""
        for attribute in ("content", "output", "text", "message"):
            if hasattr(response, attribute):
                return cls._content_text(getattr(response, attribute))
        return str(response)

    @classmethod
    def _content_text(cls, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            for key in ("text", "content", "output"):
                if key in content:
                    return cls._content_text(content[key])
            return ""
        if isinstance(content, (list, tuple)):
            parts = [cls._content_text(item) for item in content]
            return "\n".join(part for part in parts if part)
        text = getattr(content, "text", None)
        if text is not None:
            return cls._content_text(text)
        return str(content)


def build_execution_evidence_rail(
    config_base: Mapping[str, Any] | None,
) -> ExecutionEvidenceRail | None:
    """Build the strict Rail only when explicitly enabled and strict."""
    if not isinstance(config_base, Mapping):
        return None
    guard_config = config_base.get("execution_guard")
    if not isinstance(guard_config, Mapping):
        return None
    rail_config = guard_config.get("execution_evidence")
    if not isinstance(rail_config, Mapping):
        return None
    if rail_config.get("enabled") is not True:
        return None
    if rail_config.get("strict") is not True:
        return None
    return ExecutionEvidenceRail()


__all__ = ["ExecutionEvidenceRail", "build_execution_evidence_rail"]
