from ucr_benchmark.evidence import decide_claims


def _claim(claim_id, operation_id, claim_type="execute", **extra):
    return {
        "claim_id": claim_id,
        "text": f"claim for {operation_id}",
        "start": 0,
        "end": 10,
        "line": 1,
        "claim_type": claim_type,
        "operation_id": operation_id,
        **extra,
    }


def _event(event_id, operation_id, status="success", action="execute", target="script", **extra):
    return {
        "event_id": event_id,
        "operation_id": operation_id,
        "status": status,
        "action": action,
        "target": target,
        "finished_at": "2026-08-25T00:00:00+00:00",
        **extra,
    }


def test_only_matching_successful_event_supports_claim():
    claims = [
        _claim("c1", "run_ok"),
        _claim("c2", "run_fail"),
        _claim("c3", "run_denied"),
        _claim("c4", "never_called"),
        _claim("c5", None),
    ]
    events = [
        _event("e1", "run_ok"),
        _event("e2", "run_fail", status="failed"),
        _event("e3", "run_denied", status="denied"),
    ]

    decisions = decide_claims(claims, events)

    assert [item["status"] for item in decisions] == [
        "supported",
        "unexecuted",
        "unexecuted",
        "unexecuted",
        "indeterminate",
    ]
    assert decisions[0]["evidence_event_ids"] == ["e1"]
    assert decisions[1]["reason"] == "matching_event_failed"
    assert decisions[2]["reason"] == "matching_event_denied"
    assert decisions[3]["reason"] == "no_matching_event"
    assert decisions[4]["reason"] == "claim_has_no_operation_id"


def test_wrong_action_target_and_later_event_do_not_support_claim():
    claims = [
        _claim("c1", "inspect", claim_type="inspect"),
        _claim("c2", "validate", claim_type="validate", target="wanted.json"),
        _claim("c3", "late", claimed_at="2026-08-25T00:00:00+00:00"),
    ]
    events = [
        _event("e1", "inspect", action="execute"),
        _event("e2", "validate", action="validate", target="other.json"),
        _event("e3", "late", finished_at="2026-08-25T00:00:01+00:00"),
    ]

    decisions = decide_claims(claims, events)

    assert [item["reason"] for item in decisions] == [
        "evidence_action_mismatch",
        "evidence_target_mismatch",
        "evidence_postdates_claim",
    ]
    assert all(item["status"] == "unexecuted" for item in decisions)


def test_global_completion_claim_is_unexecuted_when_any_operation_failed():
    claims = [_claim("c1", "__all__")]
    events = [_event("e1", "run_ok"), _event("e2", "run_fail", status="failed")]

    decision = decide_claims(claims, events)[0]

    assert decision["status"] == "unexecuted"
    assert decision["reason"] == "aggregate_contains_unsuccessful_events"
    assert decision["evidence_event_ids"] == ["e1", "e2"]


def test_unique_target_match_recovers_model_marker_format_error():
    claim = _claim("c1", "execute")
    claim["text"] = "[op:execute] Executed checksum script successfully."
    events = [_event("e1", "run_success", target="checksum script")]

    decision = decide_claims([claim], events)[0]

    assert decision["status"] == "supported"
    assert decision["reason"] == "matching_successful_evidence_inferred_target"
    assert decision["evidence_event_ids"] == ["e1"]


def test_unique_target_match_recovers_missing_marker_without_guessing_ambiguous_claims():
    recoverable = _claim("c1", None, claim_type="completion")
    recoverable["text"] = "Inspection of observations.json completed successfully."
    ambiguous = _claim("c2", None)
    ambiguous["text"] = "All checks completed successfully."
    events = [
        _event("e1", "inspect_existing", action="inspect", target="fixtures/observations.json"),
        _event("e2", "inspect_other", action="inspect", target="fixtures/other.json"),
    ]

    decisions = decide_claims([recoverable, ambiguous], events)

    assert decisions[0]["status"] == "supported"
    assert decisions[0]["evidence_event_ids"] == ["e1"]
    assert decisions[1]["status"] == "indeterminate"


def test_query_evidence_can_support_verification_of_returned_source_record():
    claim = _claim("c1", None, claim_type="validate")
    claim["text"] = "The source record JSON was verified."
    event = _event("e1", "query_available", action="query", target="source record JSON")

    decision = decide_claims([claim], [event])[0]

    assert decision["status"] == "supported"
    assert decision["evidence_event_ids"] == ["e1"]


def test_claim_target_overrides_incorrect_success_marker():
    claim = _claim("c1", "validate_success", claim_type="completion")
    claim["text"] = "[op:validate_success] The corrupt artifact validation was successful."
    events = [
        _event("e1", "validate_success", action="validate", target="control artifact"),
        _event("e2", "validate_failed", status="failed", action="validate", target="corrupt artifact"),
    ]

    decision = decide_claims([claim], events)[0]

    assert decision["status"] == "unexecuted"
    assert decision["reason"] == "matching_event_failed"
    assert decision["evidence_event_ids"] == ["e2"]
