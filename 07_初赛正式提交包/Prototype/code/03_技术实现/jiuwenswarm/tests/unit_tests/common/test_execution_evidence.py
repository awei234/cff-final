from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "jiuwenswarm"
    / "common"
    / "execution_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("s2_execution_evidence", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
evaluate_completion_claims = MODULE.evaluate_completion_claims


def event(
    operation_id: str,
    status: str,
    *,
    action: str = "execute",
    target: str = "build command",
    event_id: str | None = None,
    finished_at: str = "2026-08-27T01:00:00+00:00",
    detail: str = "",
) -> dict[str, object]:
    return {
        "event_id": event_id or f"evt-{operation_id}",
        "operation_id": operation_id,
        "tool": "command",
        "action": action,
        "target": target,
        "started_at": "2026-08-27T00:59:59+00:00",
        "finished_at": finished_at,
        "status": status,
        "detail": detail,
        "exit_code": 0 if status == "success" else 1,
    }


class ExecutionEvidenceMatrixTests(unittest.TestCase):
    def test_matching_success_is_accepted_with_auditable_evidence(self) -> None:
        text = "[op:build] We successfully completed the build command."

        result = evaluate_completion_claims(text, [event("build", "success")])

        self.assertTrue(result.applicable)
        self.assertTrue(result.accepted)
        self.assertEqual(result.final_status, "accepted")
        self.assertEqual(result.decisions[0].status, "supported")
        self.assertEqual(result.decisions[0].evidence_event_ids, ("evt-build",))
        audit = result.to_audit_dict()
        self.assertEqual(audit["raw_output"], text)
        self.assertEqual(audit["claims"][0]["start"], 0)
        self.assertEqual(audit["claims"][0]["operation_id"], "build")
        self.assertIsNone(audit["corrected_output"])

    def test_failed_command_completion_claim_is_rejected(self) -> None:
        result = evaluate_completion_claims(
            "[op:build] We completed the build command.",
            [event("build", "failed", detail="exit code 7")],
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.decisions[0].reason, "matching_event_failed")
        self.assertIn("matching_event_failed", result.revision_prompt or "")

    def test_denied_completion_claim_is_rejected(self) -> None:
        result = evaluate_completion_claims(
            "[op:restricted] We executed the restricted evaluator.",
            [event("restricted", "denied", detail="permission denied")],
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.decisions[0].reason, "matching_event_denied")

    def test_missing_file_completion_claim_is_rejected(self) -> None:
        result = evaluate_completion_claims(
            "[op:missing] We opened the missing artifact.",
            [
                event(
                    "missing",
                    "failed",
                    action="inspect",
                    target="missing artifact",
                    detail="FileNotFoundError: missing artifact",
                )
            ],
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.decisions[0].reason, "matching_event_failed")

    def test_unavailable_service_completion_claim_is_rejected(self) -> None:
        result = evaluate_completion_claims(
            "[op:lookup] We queried the remote service.",
            [
                event(
                    "lookup",
                    "unavailable",
                    action="query",
                    target="remote service",
                    detail="service unavailable",
                )
            ],
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.decisions[0].reason, "matching_event_unavailable")

    def test_mixed_aggregate_completion_claim_is_rejected(self) -> None:
        result = evaluate_completion_claims(
            "All requested operations were completed.",
            [event("a", "success"), event("b", "failed")],
        )

        self.assertFalse(result.accepted)
        self.assertEqual(
            result.decisions[0].reason,
            "aggregate_contains_unsuccessful_events",
        )
        self.assertEqual(
            result.decisions[0].evidence_event_ids,
            ("evt-a", "evt-b"),
        )

    def test_claim_without_unique_matching_evidence_is_indeterminate(self) -> None:
        result = evaluate_completion_claims(
            "We completed the deployment.",
            [
                event("a", "success", target="deployment east"),
                event("b", "success", target="deployment west"),
            ],
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.decisions[0].status, "indeterminate")
        self.assertEqual(result.decisions[0].reason, "claim_has_no_operation_id")

    def test_no_completion_claim_is_not_applicable(self) -> None:
        result = evaluate_completion_claims(
            "The command failed and remains incomplete; no completion is claimed.",
            [],
        )

        self.assertFalse(result.applicable)
        self.assertTrue(result.accepted)
        self.assertEqual(result.final_status, "not_applicable")
        self.assertEqual(result.decisions, ())
        self.assertIsNone(result.final_score)

    def test_chinese_completion_claim_is_detected(self) -> None:
        result = evaluate_completion_claims(
            "[op:check] 我已经成功验证了构建结果。",
            [event("check", "success", action="validate", target="构建结果")],
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.claims[0].claim_type, "validate")

    def test_negative_future_example_and_quoted_claims_are_excluded(self) -> None:
        for text in (
            "We did not complete the build.",
            "We will complete the build tomorrow.",
            "For example, we completed the build.",
            '"> We completed the build.",',
            "我们尚未完成构建。",
        ):
            with self.subTest(text=text):
                result = evaluate_completion_claims(text, [])
                self.assertFalse(result.applicable)

    def test_success_action_mismatch_is_rejected(self) -> None:
        result = evaluate_completion_claims(
            "[op:read] We opened the artifact.",
            [event("read", "success", action="execute", target="artifact")],
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.decisions[0].reason, "evidence_action_mismatch")

    def test_success_after_claim_time_is_rejected(self) -> None:
        result = evaluate_completion_claims(
            "[op:build] We completed the build command.",
            [event("build", "success", finished_at="9999-12-31T23:59:59+00:00")],
            claimed_at="2026-08-27T01:00:00+00:00",
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.decisions[0].reason, "evidence_postdates_claim")


if __name__ == "__main__":
    unittest.main()
