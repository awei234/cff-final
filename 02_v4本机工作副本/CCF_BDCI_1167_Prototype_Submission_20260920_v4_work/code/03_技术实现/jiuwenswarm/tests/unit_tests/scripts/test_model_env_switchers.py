from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SWITCHER = REPO_ROOT / "scripts" / "set_model_env.py"


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw_line or raw_line.lstrip().startswith("#"):
            continue
        key, value = raw_line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def test_switcher_updates_all_model_routing_fields_atomically(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        'MODEL_PROVIDER="DeepSeek"\nAPI_BASE="https://api.deepseek.com"\n'
        'API_KEY="old-key"\nMODEL_NAME="deepseek-chat"\nUNCHANGED="yes"\n',
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(SWITCHER),
            str(env_file),
            "--provider",
            "DashScope",
            "--api-base",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "--api-key",
            "test-key",
            "--model",
            "qwen-plus",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    values = _read_env(env_file)
    assert values["MODEL_PROVIDER"] == "DashScope"
    assert values["API_BASE"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert values["API_KEY"] == "test-key"
    assert values["MODEL_NAME"] == "qwen-plus"
    assert values["UNCHANGED"] == "yes"


def test_switcher_appends_missing_fields_and_does_not_print_key(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING=1\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SWITCHER),
            str(env_file),
            "--provider",
            "OpenAICompatible",
            "--api-base",
            "https://open.bigmodel.cn/api/paas/v4",
            "--api-key",
            "do-not-print-me",
            "--model",
            "glm-test",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "do-not-print-me" not in result.stdout
    assert "do-not-print-me" not in result.stderr
    assert _read_env(env_file)["MODEL_PROVIDER"] == "OpenAICompatible"
