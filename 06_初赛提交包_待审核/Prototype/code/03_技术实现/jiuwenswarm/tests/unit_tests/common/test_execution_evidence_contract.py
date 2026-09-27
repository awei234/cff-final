from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
IMPLEMENTATION_ROOT = PROJECT_ROOT.parent
FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "execution_evidence" / "s2_01_matrix.json"
CORE_PATH = PROJECT_ROOT / "jiuwenswarm" / "common" / "execution_evidence.py"

SPEC = importlib.util.spec_from_file_location("s2_contract_execution_evidence", CORE_PATH)
assert SPEC is not None and SPEC.loader is not None
CORE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CORE
SPEC.loader.exec_module(CORE)

UCR_ROOT = IMPLEMENTATION_ROOT / "ucr_benchmark"
sys.path.insert(0, str(UCR_ROOT))
from ucr_benchmark.rail import gate_output as ucr_gate_output  # noqa: E402


class ExecutionEvidenceContractTests(unittest.TestCase):
    def test_matrix_fixture_matches_strict_acceptance_contract(self) -> None:
        cases = json.loads(FIXTURE.read_text(encoding="utf-8"))

        actual = [
            CORE.evaluate_completion_claims(case["text"], case["events"])
            for case in cases
        ]

        self.assertEqual(
            [result.final_status for result in actual],
            [
                "accepted",
                "rejected",
                "rejected",
                "rejected",
                "rejected",
                "rejected",
                "rejected",
                "not_applicable",
            ],
        )
        self.assertEqual(
            [result.applicable for result in actual],
            [True, True, True, True, True, True, True, False],
        )
        self.assertEqual(
            [result.decisions[0].reason if result.decisions else None for result in actual],
            [case["expected_reason"] for case in cases],
        )

    def test_jiuwenswarm_and_ucr_baseline_agree_on_gate_and_evidence_ids(self) -> None:
        cases = json.loads(FIXTURE.read_text(encoding="utf-8"))

        for case in cases:
            with self.subTest(case=case["id"]):
                jiuwen = CORE.evaluate_completion_claims(case["text"], case["events"])
                ucr = ucr_gate_output(case["text"], case["events"], arm="full-rail")
                self.assertEqual(jiuwen.accepted, ucr["accepted"])
                jiuwen_ids = {
                    event_id
                    for decision in jiuwen.decisions
                    for event_id in decision.evidence_event_ids
                }
                ucr_ids = {
                    event_id
                    for decision in ucr["decisions"]
                    for event_id in decision["evidence_event_ids"]
                }
                self.assertEqual(jiuwen_ids, ucr_ids)


if __name__ == "__main__":
    unittest.main()
