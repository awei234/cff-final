import json
from pathlib import Path

from ucr_benchmark.scenario_runner import read_trace, run_scenarios


def test_runner_distinguishes_success_failure_denial_and_missing(tmp_path: Path):
    manifest = {
        "version": 1,
        "scenarios": [
            {"operation_id": "run_ok", "kind": "command", "argv": ["{python}", "-c", "import sys; sys.stdout.buffer.write(b'ok\\n')"]},
            {"operation_id": "run_fail", "kind": "command", "argv": ["{python}", "-c", "raise SystemExit(7)"]},
            {"operation_id": "run_denied", "kind": "denied", "detail": "policy blocked"},
            {"operation_id": "read_missing", "kind": "read_file", "target": "fixtures/absent.txt"},
        ],
    }

    events = run_scenarios(manifest, seed=42, run_dir=tmp_path)

    assert [event["status"] for event in events] == ["success", "failed", "denied", "failed"]
    assert events[0]["exit_code"] == 0
    assert events[0]["stdout_sha256"] == "dc51b8c96c2d745df3bd5590d990230a482fd247123599548e0632fdbf97fc22"
    assert events[1]["exit_code"] == 7
    assert events[2]["detail"] == "policy blocked"
    assert events[3]["detail"].startswith("FileNotFoundError:")
    assert len({event["event_id"] for event in events}) == 4
    assert all(event["seed"] == 42 for event in events)

    persisted = read_trace(tmp_path / "tool_trace.jsonl")
    assert persisted == events
    assert all(json.loads(line) for line in (tmp_path / "tool_trace.jsonl").read_text(encoding="utf-8").splitlines())


def test_runner_hashes_successful_file_evidence(tmp_path: Path):
    fixture = tmp_path / "fixtures" / "record.txt"
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b"verified record\n")
    manifest = {"version": 1, "scenarios": [{"operation_id": "read_ok", "kind": "read_file", "target": "fixtures/record.txt"}]}

    event = run_scenarios(manifest, seed=44, run_dir=tmp_path)[0]

    assert event["status"] == "success"
    assert event["artifact_sha256"] == "4ea319d0f5cc8babf26da9ca8b131790f34648aaaac8829b328a0653ed308416"
    assert event["action"] == "inspect"
