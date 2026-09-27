#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
from pathlib import Path

from ucr_benchmark.metrics import import_legacy_metrics
from ucr_benchmark.schema import write_json


BASE = Path(__file__).resolve().parent
ARMS = ("no-rail", "prompt-only", "full-rail")
SEEDS = (42, 43, 44)


def main() -> int:
    before_root = BASE / "results" / "before" / "legacy_t4"
    after_root = BASE / "results" / "after"
    before_arms = {}
    for arm in ARMS:
        cfr_values, nfr_values, reported_ucr = [], [], []
        sources = []
        for seed in SEEDS:
            run_dir = before_root / arm / f"seed{seed}"
            legacy = import_legacy_metrics(run_dir / "citations_audit.json", run_dir / "numbers_audit.json")
            result = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
            cfr_values.append(legacy["CFR"]["value"])
            nfr_values.append(legacy["NFR"]["value"])
            reported_ucr.append(result["metrics"]["UCR"]["per_seed"][0])
            sources.append({"seed": seed, "source_hashes": legacy["source_hashes"]})
        before_arms[arm] = {
            "CFR_per_seed": cfr_values,
            "CFR_mean": round(statistics.fmean(cfr_values), 4),
            "NFR_per_seed": nfr_values,
            "NFR_mean": round(statistics.fmean(nfr_values), 4),
            "reported_UCR_per_seed": reported_ucr,
            "reported_UCR_mean": round(statistics.fmean(reported_ucr), 4),
            "reported_UCR_valid": False,
            "source_hashes": sources,
        }
    after_summary = json.loads((after_root / "summary.json").read_text(encoding="utf-8"))
    unsupported = []
    for decision_path in after_root.glob("*/seed*/ucr_decisions.json"):
        for item in json.loads(decision_path.read_text(encoding="utf-8")):
            if item["status"] == "unexecuted":
                unsupported.append({
                    "run": str(decision_path.parent.relative_to(after_root)).replace("\\", "/"),
                    "claim_id": item["claim_id"],
                    "text": item["text"],
                    "reason": item["reason"],
                    "evidence_event_ids": item["evidence_event_ids"],
                })
    comparison = {
        "root_cause": {
            "legacy_definition": "ambiguous citation lookups / citation keys",
            "correct_definition": "unexecuted execution claims / (supported + unexecuted execution claims)",
            "legacy_tool_trace_count": len(list(before_root.glob("*/seed*/tool_trace.jsonl"))),
            "after_tool_trace_count": len(list(after_root.glob("*/seed*/tool_trace.jsonl"))),
            "legacy_zero_interpretation": "invalid_dimension_not_activated",
        },
        "before": {"arms": before_arms},
        "after": after_summary,
        "observed_unexecuted_claims": unsupported,
        "cfr_nfr_note": "CFR/NFR are reproduced from immutable legacy citation/number audits; UCR scenarios report them as not measured rather than changing their values.",
    }
    write_json(BASE / "results" / "comparison.json", comparison)
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
