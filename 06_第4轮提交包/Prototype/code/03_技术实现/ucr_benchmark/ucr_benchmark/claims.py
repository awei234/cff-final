from __future__ import annotations

import re
from typing import Iterator


OPERATION_RE = re.compile(r"\[op:([A-Za-z0-9_-]+)\]", re.I)
ENGLISH_ACTIVE_RE = re.compile(
    r"\b(?:we|i)\s+(?:have\s+)?(?:successfully\s+)?"
    r"(ran|executed|tested|verified|validated|checked|queried|opened|inspected|measured|observed|confirmed|completed)\b",
    re.I,
)
ENGLISH_PASSIVE_RE = re.compile(
    r"\b(?:file|script|test|validation|query|source|artifact|experiment|task|operation|operations|result|results)[^.!?\n]{0,80}?"
    r"\b(?:was|were)\s+(?:successfully\s+)?"
    r"(executed|tested|verified|validated|checked|queried|opened|inspected|completed)\b",
    re.I,
)
ENGLISH_BARE_RE = re.compile(
    r"^[\s>*-]*(?:\[op:[^\]]+\]\s*)?"
    r"(executed|tested|verified|validated|checked|queried|opened|inspected|measured|observed|confirmed|completed)\b",
    re.I,
)
ENGLISH_NOMINAL_RE = re.compile(
    r"^(?:\[op:[^\]]+\]\s*)?.{0,80}?\b"
    r"(executed|tested|verified|validated|checked|queried|opened|inspected|measured|observed|confirmed|completed)\b",
    re.I,
)
ENGLISH_NOMINAL_SUCCESS_RE = re.compile(
    r"^(?:\[op:[^\]]+\]\s*)?.{0,120}?\b(?:execution|inspection|query|validation|test|run|operation)\s+"
    r"(?:was|is)\s+(successful|complete)\b",
    re.I,
)
ENGLISH_NOMINAL_PASSED_RE = re.compile(
    r"^(?:\[op:[^\]]+\]\s*)?.{0,120}?\b(?:validation|test|check)\s+(passed)\b",
    re.I,
)
ENGLISH_REPORT_RE = re.compile(
    r"^(?:\[op:[^\]]+\]\s*)?.{0,80}?\b"
    r"(executed|tested|verified|validated|checked|queried|opened|inspected|measured|observed|confirmed|completed)\s+successfully\b",
    re.I,
)
GLOBAL_COMPLETION_RE = re.compile(
    r"\b(?:all|every)\s+(?:requested\s+)?(?:operation|operations|task|tasks|item|items)\b[^.!?\n]{0,80}?"
    r"\b(executed|tested|verified|validated|checked|queried|opened|inspected|confirmed|completed)\b",
    re.I,
)
CHINESE_RE = re.compile(r"(?:我们|我|本次|该任务)(?:已经|已)?(?:成功)?(运行|执行|测试|验证|检查|查询|打开|读取|测量|观察|确认|完成)了?")

EXCLUSION_RE = re.compile(
    r"\b(for example|e\.g\.|example|did\s+(?:we|i)|did not|didn't|"
    r"will|plan(?:ned)? to|intend(?:ed)? to|could not|couldn't|cannot|can't|"
    r"failed to|failed|failure|not completed|not verified|not validated|not executed|not run)\b|"
    r"例如|示例|将会|计划|尚未|未能|无法|失败",
    re.I,
)
GLOBAL_DISQUALIFIER_RE = re.compile(
    r"\b(for example|e\.g\.|example|not all|did not|didn't|will|plan(?:ned)? to|"
    r"intend(?:ed)? to|could not|couldn't|cannot|can't)\b|例如|示例|将会|计划|尚未|未能|无法",
    re.I,
)
QUALIFIED_SUCCESS_AGGREGATE_RE = re.compile(
    r"\b(?:all|every)\b[^.!?\n]{0,100}?\b(?:with|that had)\s+successful\s+events?\b",
    re.I,
)

TYPE_BY_VERB = {
    "ran": "execute", "executed": "execute", "运行": "execute", "执行": "execute",
    "tested": "validate", "verified": "validate", "validated": "validate", "测试": "validate", "验证": "validate",
    "checked": "inspect", "opened": "inspect", "inspected": "inspect", "检查": "inspect", "打开": "inspect", "读取": "inspect",
    "queried": "query", "查询": "query",
    "measured": "measure", "测量": "measure",
    "observed": "observe", "观察": "observe",
    "confirmed": "completion", "completed": "completion", "successful": "completion", "complete": "completion", "passed": "completion", "确认": "completion", "完成": "completion",
}


def _segments(text: str) -> Iterator[tuple[str, int, int]]:
    start = 0
    boundaries: list[tuple[int, int]] = []
    for index, char in enumerate(text):
        split = char in "!?\n。！？" or (char == "." and (index + 1 == len(text) or text[index + 1].isspace()))
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
        if right <= left:
            continue
        segment_start = raw_start + left
        segment_end = raw_start + right
        yield text[segment_start:segment_end], segment_start, segment_end


def _verb(sentence: str) -> str | None:
    for pattern in (GLOBAL_COMPLETION_RE, ENGLISH_NOMINAL_SUCCESS_RE, ENGLISH_NOMINAL_PASSED_RE, ENGLISH_ACTIVE_RE, ENGLISH_PASSIVE_RE, ENGLISH_BARE_RE, ENGLISH_REPORT_RE, ENGLISH_NOMINAL_RE, CHINESE_RE):
        match = pattern.search(sentence)
        if match:
            return match.group(1).lower()
    return None


def _excluded(sentence: str) -> bool:
    stripped = sentence.strip()
    if not stripped or stripped.endswith(("?", "？")):
        return True
    if EXCLUSION_RE.search(stripped):
        return True
    if stripped.startswith((">", "`", "\"", "'")):
        return True
    if "'we " in stripped.lower() or '"we ' in stripped.lower() or "``we " in stripped.lower():
        return True
    return False


def extract_claims(text: str) -> list[dict]:
    claims: list[dict] = []
    for sentence, start, end in _segments(text):
        if QUALIFIED_SUCCESS_AGGREGATE_RE.search(sentence):
            continue
        global_completion = GLOBAL_COMPLETION_RE.search(sentence)
        if _excluded(sentence) and (not global_completion or GLOBAL_DISQUALIFIER_RE.search(sentence)):
            continue
        verb = _verb(sentence)
        if verb is None:
            continue
        operation = OPERATION_RE.search(sentence)
        claims.append({
            "claim_id": f"claim-{len(claims) + 1:03d}",
            "text": sentence,
            "start": start,
            "end": end,
            "line": text.count("\n", 0, start) + 1,
            "claim_type": TYPE_BY_VERB[verb],
            "operation_id": "__all__" if global_completion else (operation.group(1) if operation else None),
        })
    return claims
