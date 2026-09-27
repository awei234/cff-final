from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
HARNESS_PATH = (
    PROJECT_ROOT
    / "tests"
    / "unit_tests"
    / "agents"
    / "harness"
    / "common"
    / "test_execution_evidence_rail.py"
)
SPEC = importlib.util.spec_from_file_location("s2_rail_test_harness", HARNESS_PATH)
assert SPEC is not None and SPEC.loader is not None
HARNESS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HARNESS
SPEC.loader.exec_module(HARNESS)

RAIL_MODULE = HARNESS.RAIL_MODULE
ExecutionEvidenceRail = RAIL_MODULE.ExecutionEvidenceRail
build_execution_evidence_rail = RAIL_MODULE.build_execution_evidence_rail


class ExecutionEvidenceRailConfigTests(unittest.TestCase):
    def test_explicit_enable_builds_strict_rail(self) -> None:
        rail = build_execution_evidence_rail(
            {
                "execution_guard": {
                    "execution_evidence": {"enabled": True, "strict": True}
                }
            }
        )

        self.assertIsInstance(rail, ExecutionEvidenceRail)

    def test_disabled_config_skips_rail(self) -> None:
        rail = build_execution_evidence_rail(
            {
                "execution_guard": {
                    "execution_evidence": {"enabled": False, "strict": True}
                }
            }
        )

        self.assertIsNone(rail)

    def test_missing_config_skips_rail(self) -> None:
        self.assertIsNone(build_execution_evidence_rail({}))

    def test_non_strict_config_fails_closed_by_skipping_registration(self) -> None:
        rail = build_execution_evidence_rail(
            {
                "execution_guard": {
                    "execution_evidence": {"enabled": True, "strict": False}
                }
            }
        )

        self.assertIsNone(rail)

    def test_non_mapping_config_skips_rail(self) -> None:
        self.assertIsNone(build_execution_evidence_rail(None))


if __name__ == "__main__":
    unittest.main()
