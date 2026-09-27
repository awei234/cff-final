from openjiuwen.core.common.clients import get_client_registry
import subprocess
import sys

from jiuwenswarm.model_clients import ensure_model_clients_registered
from jiuwenswarm.model_clients.openai_compatible import OpenAICompatibleModelClient


def test_openai_compatible_client_does_not_add_deepseek_reasoning_field():
    messages = OpenAICompatibleModelClient._convert_messages_to_dict(
        [{"role": "assistant", "content": "ready"}]
    )
    assert "reasoning_content" not in messages[0]


def test_extension_client_registration_is_idempotent():
    ensure_model_clients_registered()
    ensure_model_clients_registered()
    registered = get_client_registry().list_clients()
    assert "llm_OpenAICompatible" in registered
    assert "llm_Gemini" in registered


def test_importing_jiuwenswarm_registers_extension_clients_for_all_call_paths():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import jiuwenswarm; "
            "from openjiuwen.core.common.clients import get_client_registry; "
            "print(','.join(get_client_registry().list_clients()))",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "llm_OpenAICompatible" in result.stdout
    assert "llm_Gemini" in result.stdout
