"""单测范式：构造 AgentCallbackContext + 薄 Fake，不启动 DeepAgent。
参照 tests/unit_tests/agentserver/test_stream_event_rail_symphony.py。
"""
import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # custom_rails/
from openjiuwen.core.single_agent.rail.base import AgentCallbackContext, ToolCallInputs  # noqa: E402


class FakeBuilder:
    """记录 add/remove 的 system_prompt_builder 替身。"""
    def __init__(self):
        self.sections: dict[str, object] = {}
        self.removed: list[str] = []

    def add_section(self, section):
        self.sections[section.name] = section

    def remove_section(self, name):
        self.removed.append(name)
        self.sections.pop(name, None)

    def get_section(self, name):
        return self.sections.get(name)


class FakeAgent:
    def __init__(self, workspace_root=None):
        self.system_prompt_builder = FakeBuilder()
        self.workspace_root = workspace_root or pathlib.Path(".")


class FakeSession:
    def __init__(self, sid="sess1"):
        self._sid = sid

    def get_session_id(self):
        return self._sid


class FakeToolCall:
    def __init__(self, cid="call_1"):
        self.id = cid
        self.arguments = "{}"


def make_ctx(agent=None, tool_name="write_file", tool_args=None, extra=None):
    agent = agent or FakeAgent()
    return AgentCallbackContext(
        agent=agent,
        session=FakeSession(),
        inputs=ToolCallInputs(
            tool_name=tool_name,
            tool_args=tool_args or {},
            tool_call=FakeToolCall(),
        ),
        extra=extra or {},
    )
