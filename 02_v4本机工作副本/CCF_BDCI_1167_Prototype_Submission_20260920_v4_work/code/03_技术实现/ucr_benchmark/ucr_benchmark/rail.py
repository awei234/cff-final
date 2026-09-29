from __future__ import annotations

from typing import Any

from .claims import extract_claims
from .evidence import decide_claims


ARMS = {"no-rail", "prompt-only", "full-rail", "jit-constrained"}


def _revision_prompt(decisions: list[dict[str, Any]]) -> str:
    rejected = [item for item in decisions if item["status"] != "supported"]
    lines = [
        "The execution-evidence rail rejected the draft. Revise only the claims listed below.",
        "Replace each unsupported completion statement with a truthful failure/limitation disclosure, or remove it.",
        "Do not invent a replacement result, tool call, or evidence record.",
    ]
    for item in rejected:
        lines.append(f"- [{item['reason']}] {item['text']}")
    return "\n".join(lines)


def gate_output(text: str, events: list[dict[str, Any]], arm: str = "full-rail") -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(f"unsupported arm: {arm}")
    claims = extract_claims(text)
    decisions = decide_claims(claims, events)
    enforce = arm in {"full-rail", "jit-constrained"}
    accepted = not enforce or all(item["status"] == "supported" for item in decisions)
    return {
        "arm": arm,
        "accepted": accepted,
        "claims": claims,
        "decisions": decisions,
        "revision_prompt": None if accepted else _revision_prompt(decisions),
    }
