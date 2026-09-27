from copy import deepcopy

from app.agent.graph import investigation_graph
from app.agent.grounding_validator import (
    validate_grounding,
)


TEST_FINDING_ID = 62


def build_real_state():
    """
    Build a real investigation state using Finding 62.
    """

    result = investigation_graph.invoke(
        {
            "finding_id": TEST_FINDING_ID,
            "status": "pending",
        }
    )

    if (
        result.get("status")
        != "grounding_completed"
    ):
        raise AssertionError(
            "Real investigation did not complete grounding. "
            f"status={result.get('status')}, "
            f"failed_node={result.get('failed_node')}, "
            f"error={result.get('error')}"
        )

    return result


def test_supported(
    base_state,
):
    result = validate_grounding(
        base_state
    )

    assert (
        result.status
        == "supported"
    )

    assert (
        result.score
        == 1.0
    )

    assert (
        result.grounded_verdict
        == result.original_verdict
    )

    print(
        "[PASS] supported analysis"
    )


def test_verdict_conflict(
    base_state,
):
    state = deepcopy(
        base_state
    )

    state[
        "evidence_assessment"
    ].preliminary_verdict = (
        "likely_false_positive"
    )

    state[
        "risk_enrichment"
    ].final_verdict = (
        "likely_true_positive"
    )

    result = validate_grounding(
        state
    )

    consistency_check = next(
        check
        for check in result.checks
        if (
            check.rule
            == "verdict_consistency"
        )
    )

    assert (
        consistency_check.passed
        is False
    )

    assert (
        result.status
        == "partially_supported"
    )

    assert (
        result.requires_human_review
        is True
    )

    print(
        "[PASS] verdict conflict detected"
    )


def test_unconfirmed_evidence(
    base_state,
):
    state = deepcopy(
        base_state
    )

    state[
        "evidence_assessment"
    ].evidence_status = (
        "insufficient"
    )

    result = validate_grounding(
        state
    )

    evidence_check = next(
        check
        for check in result.checks
        if (
            check.rule
            == "confirmed_evidence"
        )
    )

    assert (
        evidence_check.passed
        is False
    )

    assert (
        result.requires_human_review
        is True
    )

    print(
        "[PASS] insufficient evidence detected"
    )


def test_unsupported_exploitation_claim(
    base_state,
):
    state = deepcopy(
        base_state
    )

    intelligence = state.get(
        "intelligence_result"
    )

    if intelligence is None:
        raise AssertionError(
            "Finding 62 must include "
            "intelligence_result for this test."
        )

    intelligence.kev_records = []

    state[
        "risk_enrichment"
    ].intelligence_context = (
        "This vulnerability is actively exploited "
        "and is listed in CISA KEV."
    )

    result = validate_grounding(
        state
    )

    intelligence_check = next(
        check
        for check in result.checks
        if (
            check.rule
            == "known_exploitation_grounding"
        )
    )

    assert (
        intelligence_check.passed
        is False
    )

    assert (
        result.requires_human_review
        is True
    )

    print(
        "[PASS] unsupported exploitation claim detected"
    )

def test_unsupported_analysis(
    base_state,
):
    """
    Multiple grounding failures must trigger
    a fail-safe verdict downgrade.
    """

    state = deepcopy(
        base_state
    )

    # --------------------------------------------------
    # Failure 1: evidence is not confirmed
    # --------------------------------------------------

    state[
        "evidence_assessment"
    ].evidence_status = (
        "insufficient"
    )

    # --------------------------------------------------
    # Failure 2: evidence verdict conflicts
    # with final enrichment verdict
    # --------------------------------------------------

    state[
        "evidence_assessment"
    ].preliminary_verdict = (
        "likely_false_positive"
    )

    state[
        "risk_enrichment"
    ].final_verdict = (
        "likely_true_positive"
    )

    result = validate_grounding(
        state
    )

    assert (
        result.status
        == "unsupported"
    )

    assert (
        result.score
        < 0.5
    )

    assert (
        result.original_verdict
        == "likely_true_positive"
    )

    assert (
        result.grounded_verdict
        == "needs_review"
    )

    assert (
        result.requires_human_review
        is True
    )

    failed_checks = [
        check.rule
        for check in result.checks
        if not check.passed
    ]

    assert (
        "confirmed_evidence"
        in failed_checks
    )

    assert (
        "verdict_consistency"
        in failed_checks
    )

    print(
        "[PASS] unsupported analysis downgraded"
    )

def main():
    base_state = build_real_state()

    test_supported(
        deepcopy(base_state)
    )

    test_verdict_conflict(
        deepcopy(base_state)
    )

    test_unconfirmed_evidence(
        deepcopy(base_state)
    )

    test_unsupported_exploitation_claim(
        deepcopy(base_state)
    )

    test_unsupported_analysis(
        deepcopy(base_state)
    )
    print(
        "\nGrounding Validator evaluation PASSED"
    )


if __name__ == "__main__":
    main()