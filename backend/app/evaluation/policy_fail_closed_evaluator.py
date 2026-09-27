from app.agent.policy_engine import (
    evaluate_response_plan,
)
from app.schemas.response_plan import (
    ResponsePlan,
    ToolRequest,
)


def main():
    # --------------------------------------------------
    # Case 1:
    # Non-dry-run response plan must fail closed.
    # --------------------------------------------------

    unsafe_plan = ResponsePlan(
        finding_id=999,
        grounded_verdict="likely_true_positive",
        decision_action="recommend_remediation",
        priority="high",
        summary="Fail-closed policy test.",
        containment_plan=[],
        remediation_plan=[],
        verification_plan=[],
        tool_requests=[
            ToolRequest(
                tool_name="notify",
                target="security-team",
                reason="Test notification request.",
            )
        ],
        requires_human_review=False,

        # Deliberately unsafe.
        dry_run=False,
    )

    unsafe_result = evaluate_response_plan(
        unsafe_plan
    )

    assert unsafe_result.allow_count == 0
    assert unsafe_result.deny_count == 1
    assert unsafe_result.approval_count == 0

    assert (
        unsafe_result.results[0].decision
        == "DENY"
    )

    print(
        "[PASS] non-dry-run request denied"
    )

    # --------------------------------------------------
    # Case 2:
    # Disruptive actions must never be auto-allowed.
    # --------------------------------------------------

    block_plan = ResponsePlan(
        finding_id=999,
        grounded_verdict="likely_true_positive",
        decision_action="recommend_remediation",
        priority="high",
        summary="Disruptive action policy test.",
        containment_plan=[],
        remediation_plan=[],
        verification_plan=[],
        tool_requests=[
            ToolRequest(
                tool_name="block_ip",
                target="192.0.2.10",
                reason="Contain suspicious host.",
            )
        ],
        requires_human_review=False,
        dry_run=True,
    )

    block_result = evaluate_response_plan(
        block_plan
    )

    assert len(block_result.results) == 1

    assert (
        block_result.results[0].decision
        != "ALLOW"
    )

    assert (
        block_result.results[0].decision
        == "REQUIRE_APPROVAL"
    )

    print(
        "[PASS] disruptive request never "
        "auto-allowed"
    )

    # --------------------------------------------------
    # Case 3:
    # block_ip must be denied when investigation
    # itself still requires human review.
    # --------------------------------------------------

    review_plan = block_plan.model_copy(
        update={
            "requires_human_review": True
        }
    )

    review_result = evaluate_response_plan(
        review_plan
    )

    assert review_result.allow_count == 0
    assert review_result.deny_count == 1

    assert (
        review_result.results[0].decision
        == "DENY"
    )

    print(
        "[PASS] disruptive request denied "
        "during human review"
    )

    print(
        "\nPolicy Fail-Closed "
        "evaluation PASSED"
    )


if __name__ == "__main__":
    main()