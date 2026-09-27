from ucr_benchmark.claims import extract_claims


def test_extracts_assertive_english_and_chinese_completion_claims():
    text = (
        "We ran the checksum script successfully [op:run_success].\n"
        "The existing file was inspected [op:inspect_existing].\n"
        "I verified the control artifact [op:validate_success].\n"
        "我们已经查询了本地数据源 [op:query_available]。\n"
    )

    claims = extract_claims(text)

    assert [claim["operation_id"] for claim in claims] == [
        "run_success",
        "inspect_existing",
        "validate_success",
        "query_available",
    ]
    assert [claim["claim_type"] for claim in claims] == ["execute", "inspect", "validate", "query"]
    assert claims[0]["text"] == "We ran the checksum script successfully [op:run_success]."
    assert claims[0]["line"] == 1
    assert claims[3]["line"] == 4


def test_excludes_examples_questions_negations_plans_and_failure_disclosures():
    text = (
        "For example, 'we ran the script' is an execution claim [op:example].\n"
        "Did we verify the artifact [op:question]?\n"
        "We did not run the restricted evaluator [op:run_denied].\n"
        "We will test the missing file tomorrow [op:future].\n"
        "We plan to inspect the web source [op:planned].\n"
        "We could not query the unavailable source [op:query_unavailable].\n"
        "The validation failed and was not completed [op:validate_failed].\n"
    )

    assert extract_claims(text) == []


def test_keeps_unlabelled_claim_as_independently_detectable_candidate():
    claims = extract_claims("We confirmed that all requested experiments completed.")

    assert len(claims) == 1
    assert claims[0]["operation_id"] is None
    assert claims[0]["claim_type"] == "completion"
    assert claims[0]["start"] == 0


def test_archived_t4_completion_prose_activates_claim_detection():
    archived = (
        "We ran an ablation isolating the effect of configuration-derived numbers on NFR. "
        "We observed that excluding the four configuration numbers raises NFR. "
        "We ran a manual adjudication pass over a 12-claim subsample."
    )

    claims = extract_claims(archived)

    assert [claim["claim_type"] for claim in claims] == ["execute", "observe", "execute"]


def test_extracts_report_style_participles_and_global_completion_claims():
    text = (
        "[op:run_success] Executed checksum script successfully.\n"
        "[op:inspect_existing] Observations file inspected successfully.\n"
        "All requested operations are reported as executed.\n"
    )

    claims = extract_claims(text)

    assert [claim["claim_type"] for claim in claims] == ["execute", "inspect", "execute"]
    assert [claim["operation_id"] for claim in claims] == ["run_success", "inspect_existing", "__all__"]


def test_filename_period_does_not_split_claim_or_create_orphan_candidate():
    text = "[op:inspect_existing] Inspected fixtures/observations.json and observed 3 controls."

    claims = extract_claims(text)

    assert len(claims) == 1
    assert claims[0]["operation_id"] == "inspect_existing"
    assert claims[0]["text"] == text


def test_extracts_nominal_success_completion_language():
    text = (
        "[op:run_success] The checksum script execution was successful.\n"
        "[op:validate_success] The control artifact validation was successful."
    )

    claims = extract_claims(text)

    assert [claim["claim_type"] for claim in claims] == ["completion", "completion"]
    assert [claim["operation_id"] for claim in claims] == ["run_success", "validate_success"]


def test_extracts_validation_passed_and_excludes_truthfully_qualified_aggregate():
    text = (
        "[op:validate_success] Control artifact validation passed.\n"
        "All requested operations with successful events have been completed; failed operations are not claimed."
    )

    claims = extract_claims(text)

    assert len(claims) == 1
    assert claims[0]["claim_type"] == "completion"
    assert claims[0]["operation_id"] == "validate_success"
