"""Summarize the real resource consumption of a research-matrix run.

Usage: python summarize_v5_run.py <run_dir>
Reads only; prints a JSON summary (provider calls, tokens, latency, retrieval, UCR durations).
"""
import json
import sys
from pathlib import Path

TOPICS = ("context-engineering", "memory-engine", "self-evolution")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    run = Path(sys.argv[1])
    trace = [
        json.loads(line)
        for line in (run / "provider_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    out = {
        "run_dir": run.as_posix(),
        "provider": "deepseek",
        "models": sorted({t.get("model") for t in trace}),
        "provider_calls": len(trace),
        "prompt_tokens": sum(t.get("prompt_tokens") or 0 for t in trace),
        "completion_tokens": sum(t.get("completion_tokens") or 0 for t in trace),
        "total_tokens": sum(t.get("total_tokens") or 0 for t in trace),
        "total_latency_seconds": round(sum(t.get("duration_seconds", 0) for t in trace), 3),
        "calls": [
            {
                "call_index": t.get("call_index"),
                "topic_id": t.get("topic_id"),
                "stage": t.get("stage"),
                "duration_seconds": t.get("duration_seconds"),
                "prompt_tokens": t.get("prompt_tokens"),
                "completion_tokens": t.get("completion_tokens"),
                "total_tokens": t.get("total_tokens"),
            }
            for t in trace
        ],
        "topics": {},
    }
    for tid in TOPICS:
        td = run / tid
        mat = json.loads((td / "research_materials.json").read_text(encoding="utf-8"))
        ex = json.loads((td / "experiment_results.json").read_text(encoding="utf-8"))
        out["topics"][tid] = {
            "retrieval_status": mat.get("retrieval_status"),
            "candidate_count": (mat.get("deduplication") or {}).get("candidate_count"),
            "kept_count": (mat.get("deduplication") or {}).get("kept_count"),
            "removed_duplicates": (mat.get("deduplication") or {}).get("removed_duplicates"),
            "retrieval_failures": [
                {"provider": f.get("provider"), "status": f.get("status"), "error": f.get("error")}
                for f in mat.get("failures", [])
            ],
            "ucr_arm_durations": {a.get("arm"): a.get("duration_seconds") for a in ex.get("arms", [])},
            "ucr_total_seconds": round(sum(a.get("duration_seconds", 0) for a in ex.get("arms", [])), 3),
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
