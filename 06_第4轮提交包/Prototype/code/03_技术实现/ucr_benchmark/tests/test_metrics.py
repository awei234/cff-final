from ucr_benchmark.metrics import compute_ucr


def _decisions(statuses):
    return [{"status": status} for status in statuses]


def test_measured_zero_requires_supported_denominator():
    metric = compute_ucr(_decisions(["supported", "supported", "supported"]))

    assert metric == {
        "value": 0.0,
        "numerator": 0,
        "denominator": 3,
        "supported": 3,
        "unexecuted": 0,
        "indeterminate": 0,
        "activated": True,
        "status": "measured",
        "reason": None,
    }


def test_ucr_counts_only_supported_and_unexecuted_claims():
    metric = compute_ucr(_decisions(["unexecuted", "unexecuted", "supported", "indeterminate"]))

    assert metric["value"] == 0.6667
    assert metric["numerator"] == 2
    assert metric["denominator"] == 3
    assert metric["indeterminate"] == 1


def test_no_claims_is_not_applicable_instead_of_zero():
    assert compute_ucr([]) == {
        "value": None,
        "numerator": 0,
        "denominator": 0,
        "supported": 0,
        "unexecuted": 0,
        "indeterminate": 0,
        "activated": False,
        "status": "not_applicable",
        "reason": "no_detectable_claims",
    }


def test_only_indeterminate_claims_is_not_applicable():
    metric = compute_ucr(_decisions(["indeterminate", "indeterminate"]))

    assert metric["value"] is None
    assert metric["reason"] == "only_indeterminate_claims"
    assert metric["activated"] is False
