from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import re
from typing import Any, Mapping, Sequence


_OPERATION_RE = re.compile(r"\[op:([A-Za-z0-9_.:-]+)\]", re.IGNORECASE)
_ENGLISH_ACTIVE_RE = re.compile(
    r"\b(?:we|i)\s+(?:have\s+)?(?:successfully\s+)?"
    r"(ran|executed|tested|verified|validated|checked|queried|opened|"
    r"inspected|measured|observed|confirmed|completed)\b",
    re.IGNORECASE,
)
_ENGLISH_PASSIVE_RE = re.compile(
    r"\b(?:file|script|test|validation|query|source|artifact|experiment|"
    r"task|operation|operations|result|results|command|build)"
    r"[^.!?\n]{0,100}?\b(?:was|were)\s+(?:successfully\s+)?"
    r"(executed|tested|verified|validated|checked|queried|opened|inspected|completed)\b",
    re.IGNORECASE,
)
_ENGLISH_NOMINAL_SUCCESS_RE = re.compile(
    r"^(?:\[op:[^\]]+\]\s*)?.{0,120}?\b"
    r"(?:execution|inspection|query|validation|test|run|operation|build|command)\s+"
    r"(?:was|is)\s+(successful|complete)\b",
    re.IGNORECASE,
)
_ENGLISH_PASSED_RE = re.compile(
    r"^(?:\[op:[^\]]+\]\s*)?.{0,120}?\b(?:validation|test|check)\s+(passed)\b",
    re.IGNORECASE,
)
_GLOBAL_COMPLETION_RE = re.compile(
    r"\b(?:all|every)\s+(?:requested\s+)?"
    r"(?:operation|operations|task|tasks|item|items)\b[^.!?\n]{0,100}?"
    r"\b(executed|tested|verified|validated|checked|queried|opened|"
    r"inspected|confirmed|completed)\b",
    re.IGNORECASE,
)
_CHINESE_RE = re.compile(
    r"(?:我们|我|本次|该任务)(?:已经|已)?(?:成功)?"
    r"(运行|执行|测试|验证|检查|查询|打开|读取|测量|观察|确认|完成)了?"
)
_EXCLUSION_RE = re.compile(
    r"\b(for example|e\.g\.|example|did\s+(?:we|i)|did not|didn't|"
    r"will|plan(?:ned)?\s+to|intend(?:ed)?\s+to|could not|couldn't|"
    r"cannot|can't|failed to|failed|failure|not completed|not verified|"
    r"not validated|not executed|not run|remains incomplete|no completion)\b|"
    r"例如|示例|将会|计划|尚未|未能|无法|失败",
    re.IGNORECASE,
)
_GLOBAL_DISQUALIFIER_RE = re.compile(
    r"\b(for example|e\.g\.|example|not all|did not|didn't|will|"
    r"plan(?:ned)?\s+to|intend(?:ed)?\s+to|could not|couldn't|cannot|can't)\b|"
    r"例如|示例|将会|计划|尚未|未能|无法",
    re.IGNORECASE,
)
_QUALIFIED_SUCCESS_AGGREGATE_RE = re.compile(
    r"\b(?:all|every)\b[^.!?\n]{0,100}?\b(?:with|that had)\s+successful\s+events?\b",
    re.IGNORECASE,
)

_TYPE_BY_VERB = {
    "ran": "execute",
    "executed": "execute",
    "运行": "execute",
    "执行": "execute",
    "tested": "validate",
    "verified": "validate",
    "validated": "validate",
    "测试": "validate",
    "验证": "validate",
    "checked": "inspect",
    "opened": "inspect",
    "inspected": "inspect",
    "检查": "inspect",
    "打开": "inspect",
    "读取": "inspect",
    "queried": "query",
    "查询": "query",
    "measured": "measure",
    "测量": "measure",
    "observed": "observe",
    "观察": "observe",
    "confirmed": "completion",
    "completed": "completion",
    "successful": "completion",
    "complete": "completion",
    "passed": "completion",
    "确认": "completion",
    "完成": "completion",
}

_ACTION_COMPATIBILITY = {
    "execute": frozenset({"execute"}),
    "validate": frozenset({"validate", "test", "query", "inspect"}),
    "inspect": frozenset({"inspect", "open", "read", "check"}),
    "query": frozenset({"query", "search", "lookup"}),
    "measure": frozenset({"execute", "validate", "inspect", "query", "measure"}),
    "observe": frozenset({"execute", "validate", "inspect", "query", "observe"}),
    "completion": frozenset({"execute", "validate", "inspect", "query", "complete"}),
}

_UNSUCCESSFUL_REASONS = {
    "failed": "matching_event_failed",
    "denied": "matching_event_denied",
    "unavailable": "matching_event_unavailable",
    "indeterminate": "matching_event_indeterminate",
    "not_called": "matching_event_not_called",
}


@dataclass(frozen=True)
class ExecutionEvidenceEvent:
    event_id: str
    operation_id: str
    tool: str
    action: str
    target: str
    started_at: str
    finished_at: str
    status: str
    detail: str = ""
    exit_code: int | None = None


@dataclass(frozen=True)
class CompletionClaim:
    claim_id: str
    text: str
    start: int
    end: int
    line: int
    claim_type: str
    operation_id: str | None
    claimed_at: str | None = None


@dataclass(frozen=True)
class ClaimDecision:
    claim_id: str
    text: str
    start: int
    end: int
    line: int
    claim_type: str
    operation_id: str | None
    status: str
    evidence_event_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class GateResult:
    applicable: bool
    accepted: bool
    claims: tuple[CompletionClaim, ...]
    decisions: tuple[ClaimDecision, ...]
    rejection_reasons: tuple[str, ...]
    revision_prompt: str | None
    final_status: str
    raw_output: str
    corrected_output: None = None
    final_score: float | None = None

    def to_audit_dict(self) -> dict[str, Any]:
        return asdict(self)


def _segments(text: str) -> list[tuple[str, int, int]]:
    segments: list[tuple[str, int, int]] = []
    start = 0
    boundaries: list[tuple[int, int]] = []
    for index, char in enumerate(text):
        split = char in "!?\n。！？" or (
            char == "." and (index + 1 == len(text) or text[index + 1].isspace())
        )
        if split:
            end = index if char == "\n" else index + 1
            boundaries.append((start, end))
            start = index + 1
    if start < len(text):
        boundaries.append((start, len(text)))
    for raw_start, raw_end in boundaries:
        raw = text[raw_start:raw_end]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        if right > left:
            segment_start = raw_start + left
            segment_end = raw_start + right
            segments.append((text[segment_start:segment_end], segment_start, segment_end))
    return segments


def _completion_verb(sentence: str) -> str | None:
    for pattern in (
        _GLOBAL_COMPLETION_RE,
        _ENGLISH_NOMINAL_SUCCESS_RE,
        _ENGLISH_PASSED_RE,
        _ENGLISH_ACTIVE_RE,
        _ENGLISH_PASSIVE_RE,
        _CHINESE_RE,
    ):
        match = pattern.search(sentence)
        if match:
            return match.group(1).lower()
    return None


def _is_excluded(sentence: str, global_completion: re.Match[str] | None) -> bool:
    stripped = sentence.strip()
    if not stripped or stripped.endswith(("?", "？")):
        return True
    if stripped.startswith((">", "`", '"', "'")):
        return True
    if "'we " in stripped.lower() or '"we ' in stripped.lower() or "``we " in stripped.lower():
        return True
    if _EXCLUSION_RE.search(stripped):
        return global_completion is None or _GLOBAL_DISQUALIFIER_RE.search(stripped) is not None
    return False


def extract_completion_claims(text: str) -> list[CompletionClaim]:
    claims: list[CompletionClaim] = []
    for sentence, start, end in _segments(text):
        if _QUALIFIED_SUCCESS_AGGREGATE_RE.search(sentence):
            continue
        global_completion = _GLOBAL_COMPLETION_RE.search(sentence)
        if _is_excluded(sentence, global_completion):
            continue
        verb = _completion_verb(sentence)
        if verb is None:
            continue
        operation = _OPERATION_RE.search(sentence)
        claims.append(
            CompletionClaim(
                claim_id=f"claim-{len(claims) + 1:03d}",
                text=sentence,
                start=start,
                end=end,
                line=text.count("\n", 0, start) + 1,
                claim_type=_TYPE_BY_VERB[verb],
                operation_id=(
                    "__all__"
                    if global_completion
                    else (operation.group(1) if operation else None)
                ),
            )
        )
    return claims


def _coerce_event(value: ExecutionEvidenceEvent | Mapping[str, Any]) -> ExecutionEvidenceEvent:
    if isinstance(value, ExecutionEvidenceEvent):
        return value
    return ExecutionEvidenceEvent(
        event_id=str(value.get("event_id", "")),
        operation_id=str(value.get("operation_id", "")),
        tool=str(value.get("tool", "")),
        action=str(value.get("action", "")),
        target=str(value.get("target", "")),
        started_at=str(value.get("started_at", "")),
        finished_at=str(value.get("finished_at", "")),
        status=str(value.get("status", "indeterminate")).strip().lower(),
        detail=str(value.get("detail", "")),
        exit_code=value.get("exit_code") if isinstance(value.get("exit_code"), int) else None,
    )


def _target_tokens(value: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", value.lower()))
    ordinary = {
        "the", "a", "an", "file", "artifact", "experiment", "script",
        "command", "operation", "operations", "we", "i", "completed",
    }
    distinctive = tokens - ordinary
    return distinctive or tokens


def _infer_by_target(
    claim: CompletionClaim,
    events: Sequence[ExecutionEvidenceEvent],
) -> list[ExecutionEvidenceEvent]:
    claim_tokens = _target_tokens(claim.text)
    scored: list[tuple[int, ExecutionEvidenceEvent]] = []
    for event in events:
        overlap = len(claim_tokens & _target_tokens(event.target))
        if overlap:
            scored.append((overlap, event))
    if not scored:
        return []
    best = max(score for score, _ in scored)
    winners = [event for score, event in scored if score == best]
    return winners if len(winners) == 1 else []


def _decision(
    claim: CompletionClaim,
    status: str,
    reason: str,
    events: Sequence[ExecutionEvidenceEvent],
) -> ClaimDecision:
    return ClaimDecision(
        claim_id=claim.claim_id,
        text=claim.text,
        start=claim.start,
        end=claim.end,
        line=claim.line,
        claim_type=claim.claim_type,
        operation_id=claim.operation_id,
        status=status,
        evidence_event_ids=tuple(event.event_id for event in events),
        reason=reason,
    )


def _decide_claim(
    claim: CompletionClaim,
    events: Sequence[ExecutionEvidenceEvent],
) -> ClaimDecision:
    if claim.operation_id == "__all__":
        if events and all(event.status == "success" for event in events):
            return _decision(claim, "supported", "aggregate_all_events_successful", events)
        return _decision(
            claim,
            "rejected",
            "aggregate_contains_unsuccessful_events",
            events,
        )

    inferred = False
    if claim.operation_id:
        matching = [event for event in events if event.operation_id == claim.operation_id]
    else:
        matching = _infer_by_target(claim, events)
        inferred = bool(matching)
        if not matching:
            return _decision(claim, "indeterminate", "claim_has_no_operation_id", ())

    if not matching:
        return _decision(claim, "rejected", "no_matching_event", ())

    successful = [event for event in matching if event.status == "success"]
    if not successful:
        statuses = {event.status for event in matching}
        for event_status in ("denied", "unavailable", "failed", "indeterminate", "not_called"):
            if event_status in statuses:
                return _decision(
                    claim,
                    "indeterminate" if event_status == "indeterminate" else "rejected",
                    _UNSUCCESSFUL_REASONS[event_status],
                    matching,
                )
        return _decision(claim, "indeterminate", "matching_event_indeterminate", matching)

    compatible_actions = _ACTION_COMPATIBILITY.get(claim.claim_type, frozenset())
    compatible = [event for event in successful if event.action in compatible_actions]
    if not compatible:
        return _decision(claim, "rejected", "evidence_action_mismatch", matching)

    if claim.claimed_at:
        preceding = [event for event in compatible if event.finished_at <= claim.claimed_at]
        if not preceding:
            return _decision(claim, "rejected", "evidence_postdates_claim", matching)
        compatible = preceding

    reason = "matching_successful_evidence_inferred_target" if inferred else "matching_successful_evidence"
    return _decision(claim, "supported", reason, compatible)


def _revision_prompt(decisions: Sequence[ClaimDecision]) -> str:
    lines = [
        "The execution-evidence rail rejected the draft. Revise only the claims listed below.",
        "Replace each unsupported completion statement with a truthful failure or limitation disclosure, or remove it.",
        "Do not invent a replacement result, tool call, or evidence record.",
    ]
    for decision in decisions:
        if decision.status != "supported":
            lines.append(f"- [{decision.reason}] {decision.text}")
    return "\n".join(lines)


def evaluate_completion_claims(
    text: str,
    events: Sequence[ExecutionEvidenceEvent | Mapping[str, Any]],
    *,
    claimed_at: str | None = None,
) -> GateResult:
    raw_output = str(text or "")
    claims = extract_completion_claims(raw_output)
    if claimed_at:
        claims = [replace(claim, claimed_at=claimed_at) for claim in claims]
    if not claims:
        return GateResult(
            applicable=False,
            accepted=True,
            claims=(),
            decisions=(),
            rejection_reasons=(),
            revision_prompt=None,
            final_status="not_applicable",
            raw_output=raw_output,
            final_score=None,
        )

    normalized_events = tuple(_coerce_event(event) for event in events)
    decisions = tuple(_decide_claim(claim, normalized_events) for claim in claims)
    accepted = all(decision.status == "supported" for decision in decisions)
    reasons = tuple(
        dict.fromkeys(
            decision.reason for decision in decisions if decision.status != "supported"
        )
    )
    return GateResult(
        applicable=True,
        accepted=accepted,
        claims=tuple(claims),
        decisions=decisions,
        rejection_reasons=reasons,
        revision_prompt=None if accepted else _revision_prompt(decisions),
        final_status="accepted" if accepted else "rejected",
        raw_output=raw_output,
        final_score=1.0 if accepted else 0.0,
    )


__all__ = [
    "ClaimDecision",
    "CompletionClaim",
    "ExecutionEvidenceEvent",
    "GateResult",
    "evaluate_completion_claims",
    "extract_completion_claims",
]
