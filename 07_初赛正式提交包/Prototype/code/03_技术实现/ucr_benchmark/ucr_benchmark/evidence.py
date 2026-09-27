from __future__ import annotations

import re
from typing import Any


ACTION_COMPATIBILITY = {
    "execute": {"execute"},
    "validate": {"validate", "test", "query", "inspect"},
    "inspect": {"inspect", "open", "read", "check"},
    "query": {"query", "search", "lookup"},
    "measure": {"execute", "validate", "inspect", "query", "measure"},
    "observe": {"execute", "validate", "inspect", "query", "observe"},
    "completion": {"execute", "validate", "inspect", "query", "complete"},
}


def _target(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9._/-]+", value.lower()))


def _target_tokens(value: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", value.lower()))
    distinctive = tokens - {"the", "a", "an", "fixtures", "json", "file", "artifact", "experiment", "script"}
    return distinctive or tokens


def _infer_by_target(claim: dict[str, Any], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claim_tokens = _target_tokens(str(claim.get("text", "")))
    scored = []
    for event in events:
        overlap = len(claim_tokens & _target_tokens(str(event.get("target", ""))))
        if overlap:
            scored.append((overlap, event))
    if not scored:
        return []
    best = max(score for score, _ in scored)
    winners = [event for score, event in scored if score == best]
    return winners if len(winners) == 1 else []


def _decision(claim: dict[str, Any], status: str, reason: str, event_ids: list[str]) -> dict[str, Any]:
    return {
        **claim,
        "status": status,
        "evidence_event_ids": event_ids,
        "reason": reason,
    }


def decide_claims(claims: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for claim in claims:
        operation_id = claim.get("operation_id")
        inferred = False
        if not operation_id:
            matching = _infer_by_target(claim, events)
            inferred = bool(matching)
            if not matching:
                decisions.append(_decision(claim, "indeterminate", "claim_has_no_operation_id", []))
                continue
        if operation_id == "__all__":
            event_ids = [str(event["event_id"]) for event in events]
            if events and all(event.get("status") == "success" for event in events):
                decisions.append(_decision(claim, "supported", "aggregate_all_events_successful", event_ids))
            else:
                decisions.append(_decision(claim, "unexecuted", "aggregate_contains_unsuccessful_events", event_ids))
            continue
        if operation_id:
            matching = [event for event in events if event.get("operation_id") == operation_id]
            target_inferred = _infer_by_target(claim, events)
            if matching and target_inferred and target_inferred[0].get("operation_id") != operation_id:
                matching = target_inferred
                inferred = True
            if not matching:
                matching = target_inferred
                inferred = bool(matching)
        matching_ids = [str(event["event_id"]) for event in matching]
        if not matching:
            decisions.append(_decision(claim, "unexecuted", "no_matching_event", []))
            continue
        successful = [event for event in matching if event.get("status") == "success"]
        if not successful:
            statuses = {str(event.get("status")) for event in matching}
            if "denied" in statuses:
                reason = "matching_event_denied"
            elif "failed" in statuses:
                reason = "matching_event_failed"
            else:
                reason = "matching_event_not_called"
            decisions.append(_decision(claim, "unexecuted", reason, matching_ids))
            continue
        compatible_actions = ACTION_COMPATIBILITY.get(str(claim.get("claim_type")), set())
        compatible = [event for event in successful if event.get("action") in compatible_actions]
        if not compatible:
            decisions.append(_decision(claim, "unexecuted", "evidence_action_mismatch", matching_ids))
            continue
        expected_target = claim.get("target")
        if expected_target:
            target_matches = [event for event in compatible if _target(str(event.get("target", ""))) == _target(str(expected_target))]
            if not target_matches:
                decisions.append(_decision(claim, "unexecuted", "evidence_target_mismatch", matching_ids))
                continue
            compatible = target_matches
        claimed_at = claim.get("claimed_at")
        if claimed_at:
            preceding = [event for event in compatible if str(event.get("finished_at", "")) <= str(claimed_at)]
            if not preceding:
                decisions.append(_decision(claim, "unexecuted", "evidence_postdates_claim", matching_ids))
                continue
            compatible = preceding
        reason = "matching_successful_evidence_inferred_target" if inferred else "matching_successful_evidence"
        decisions.append(_decision(claim, "supported", reason, [str(event["event_id"]) for event in compatible]))
    return decisions
