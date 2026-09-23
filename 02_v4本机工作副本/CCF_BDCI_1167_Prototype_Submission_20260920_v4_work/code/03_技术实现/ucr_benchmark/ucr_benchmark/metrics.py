from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from .schema import sha256_bytes


VALID_DECISIONS = {"supported", "unexecuted", "indeterminate"}


def compute_ucr(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(item.get("status")) for item in decisions)
    invalid = set(counts) - VALID_DECISIONS
    if invalid:
        raise ValueError(f"invalid UCR decision statuses: {sorted(invalid)}")
    supported = counts["supported"]
    unexecuted = counts["unexecuted"]
    indeterminate = counts["indeterminate"]
    denominator = supported + unexecuted
    if denominator:
        value = round(unexecuted / denominator, 4)
        status = "measured"
        reason = None
        activated = True
    else:
        value = None
        status = "not_applicable"
        reason = "only_indeterminate_claims" if indeterminate else "no_detectable_claims"
        activated = False
    return {
        "value": value,
        "numerator": unexecuted,
        "denominator": denominator,
        "supported": supported,
        "unexecuted": unexecuted,
        "indeterminate": indeterminate,
        "activated": activated,
        "status": status,
        "reason": reason,
    }


def import_legacy_metrics(
    citations_path: Path,
    numbers_path: Path,
    expected_hashes: dict[str, str] | None = None,
) -> dict[str, Any]:
    paths = (citations_path, numbers_path)
    hashes = {path.name: sha256_bytes(path.read_bytes()) for path in paths}
    if expected_hashes is not None and hashes != expected_hashes:
        raise ValueError(f"legacy source hash mismatch: expected {expected_hashes}, got {hashes}")
    citation_summary = json.loads(citations_path.read_text(encoding="utf-8"))["summary"]
    number_summary = json.loads(numbers_path.read_text(encoding="utf-8"))["summary"]

    def ratio(numerator: int, denominator: int) -> dict[str, Any]:
        return {
            "value": round(numerator / denominator, 4) if denominator else None,
            "numerator": numerator,
            "denominator": denominator,
        }

    citation_total = int(citation_summary["total"])
    citation_not_found = int(citation_summary["not_found"])
    number_total = int(number_summary["total"])
    number_fabricated = int(number_summary["fabricated"])
    return {
        "CFR": ratio(citation_not_found, citation_total),
        "NFR": ratio(number_fabricated, number_total),
        "source_hashes": hashes,
    }
