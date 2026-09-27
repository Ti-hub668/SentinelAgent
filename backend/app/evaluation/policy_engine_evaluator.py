from app.agent.approval import (
    approve_request,
    reject_request,
)
from app.agent.policy_engine import (
    build_approval_requests,
    evaluate_response_plan,
)
from app.schemas.response_plan import (
    ResponsePlan,
    ToolRequest,
)


def build_plan(
    *,
    requires_human_review: bool,
    requests: list[ToolRequest],
) -> ResponsePlan:
    return ResponsePlan(
        finding_id=62,
        grounded_verdict=(
            "likely_true_positive"
        ),
        decision_action=(
            "recommend_remediation"
        ),
        priority="medium",
        summary="Policy evaluation test.",
        containment_plan=[],
        remediation_plan=[],
        verification_plan=[],
        tool_requests=requests,
        requires_human_review=(
            requires_human_review
        ),
        dry_run=True,
    )


def test_non_disruptive_allow():
    plan = build_plan(
        requires_human_review=False,
        requests=[
            ToolRequest(
                tool_name="create_ticket",
                target="127.0.0.1",
                reason="Create remediation ticket.",
            ),
            ToolRequest(
                tool_name="notify",
                target="security-team",
                reason="Notify analyst team.",
            ),
        ],
    )

    result = evaluate_response_plan(
        plan
    )

    assert result.allow_count == 2
    assert result.deny_count == 0
    assert result.approval_count == 0

    assert all(
        item.decision == "ALLOW"
        for item in result.results
    )

    print(
        "[PASS] non-disruptive actions allowed"
    )


def test_block_ip_requires_approval():
    plan = build_plan(
        requires_human_review=False,
        requests=[
            ToolRequest(
                tool_name="block_ip",
                target="192.0.2.10",
                reason="Contain malicious host.",
            ),
        ],
    )

    result = evaluate_response_plan(
        plan
    )

    assert result.allow_count == 0
    assert result.deny_count == 0
    assert result.approval_count == 1

    assert (
        result.results[0].decision
        == "REQUIRE_APPROVAL"
    )

    approvals = build_approval_requests(
        result
    )

    assert len(approvals) == 1
    assert approvals[0].status == "pending"

    approved = approve_request(
        approvals[0],
        reviewer="security-analyst",
        reason="Containment validated.",
    )

    assert approved.status == "approved"

    print(
        "[PASS] disruptive action requires approval"
    )


def test_block_ip_denied_during_review():
    plan = build_plan(
        requires_human_review=True,
        requests=[
            ToolRequest(
                tool_name="block_ip",
                target="192.0.2.10",
                reason="Contain target.",
            ),
        ],
    )

    result = evaluate_response_plan(
        plan
    )

    assert result.deny_count == 1

    assert (
        result.results[0].decision
        == "DENY"
    )

    print(
        "[PASS] block_ip denied during review"
    )


def test_manual_review():
    plan = build_plan(
        requires_human_review=True,
        requests=[
            ToolRequest(
                tool_name="manual_review",
                target="finding:62",
                reason="Analyst review required.",
            ),
        ],
    )

    result = evaluate_response_plan(
        plan
    )

    assert result.approval_count == 1

    approvals = build_approval_requests(
        result
    )

    assert len(approvals) == 1

    rejected = reject_request(
        approvals[0],
        reviewer="security-analyst",
        reason="More evidence required.",
    )

    assert rejected.status == "rejected"

    print(
        "[PASS] manual review approval workflow"
    )


def main():
    test_non_disruptive_allow()

    test_block_ip_requires_approval()

    test_block_ip_denied_during_review()

    test_manual_review()

    print(
        "\nPolicy Engine evaluation PASSED"
    )


if __name__ == "__main__":
    main()