import hashlib
import json
from pathlib import Path

import pytest

from ucr_benchmark.metrics import import_legacy_metrics


def test_legacy_cfr_nfr_are_derived_without_ucr_reinterpretation(tmp_path: Path):
    citations = tmp_path / "citations_audit.json"
    numbers = tmp_path / "numbers_audit.json"
    citations.write_text(json.dumps({"summary": {"total": 18, "not_found": 0, "ambiguous": 0}}), encoding="utf-8")
    numbers.write_text(json.dumps({"summary": {"total": 42, "fabricated": 21}}), encoding="utf-8")

    result = import_legacy_metrics(citations, numbers)

    assert result["CFR"] == {"value": 0.0, "numerator": 0, "denominator": 18}
    assert result["NFR"] == {"value": 0.5, "numerator": 21, "denominator": 42}
    assert "UCR" not in result
    assert result["source_hashes"]["citations_audit.json"] == hashlib.sha256(citations.read_bytes()).hexdigest()


def test_legacy_import_rejects_changed_source_hash(tmp_path: Path):
    citations = tmp_path / "citations_audit.json"
    numbers = tmp_path / "numbers_audit.json"
    citations.write_text(json.dumps({"summary": {"total": 10, "not_found": 1}}), encoding="utf-8")
    numbers.write_text(json.dumps({"summary": {"total": 10, "fabricated": 2}}), encoding="utf-8")
    expected = {
        "citations_audit.json": hashlib.sha256(citations.read_bytes()).hexdigest(),
        "numbers_audit.json": hashlib.sha256(numbers.read_bytes()).hexdigest(),
    }
    citations.write_text(json.dumps({"summary": {"total": 10, "not_found": 9}}), encoding="utf-8")

    with pytest.raises(ValueError, match="legacy source hash mismatch"):
        import_legacy_metrics(citations, numbers, expected_hashes=expected)
