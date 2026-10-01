from app.agent.approval import (
    approve_request,
    reject_request,
)
from app.agent.policy_engine import (
    build_approval_requests,
    evaluate_response_plan,
)
from app.agent.tool_broker import (
    execute_policy_evaluation,
)
from app.schemas.response_plan import (
    ResponsePlan,
    ToolRequest,
)


def make_plan(
    *,
    request: ToolRequest,
    requires_human_review: bool = False,
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
        summary="Tool Broker evaluator.",
        containment_plan=[],
        remediation_plan=[],
        verification_plan=[],
        tool_requests=[request],
        requires_human_review=(
            requires_human_review
        ),
        dry_run=True,
    )


def test_allow():
    plan = make_plan(
        request=ToolRequest(
            tool_name="create_ticket",
            target="finding:62",
            reason="Create remediation ticket.",
        ),
    )

    policy = evaluate_response_plan(plan)

    assert (
        policy.results[0].decision
        == "ALLOW"
    )

    result = execute_policy_evaluation(
        policy,
        approvals=[],
    )

    assert result.simulated_count == 1
    assert result.blocked_count == 0

    assert result.results[0].authorized is True
    assert result.results[0].dry_run is True

    print(
        "[PASS] ALLOW request reached "
        "dry-run adapter"
    )


def test_pending_approval():
    plan = make_plan(
        request=ToolRequest(
            tool_name="block_ip",
            target="192.0.2.10",
            reason="Contain suspicious host.",
        ),
    )

    policy = evaluate_response_plan(plan)

    approvals = build_approval_requests(
        policy
    )

    result = execute_policy_evaluation(
        policy,
        approvals=approvals,
    )

    assert result.simulated_count == 0
    assert result.blocked_count == 1

    assert (
        result.results[0].authorized
        is False
    )

    print(
        "[PASS] pending approval blocked"
    )


def test_approved_request():
    plan = make_plan(
        request=ToolRequest(
            tool_name="block_ip",
            target="192.0.2.10",
            reason="Contain suspicious host.",
        ),
    )

    policy = evaluate_response_plan(plan)

    approvals = build_approval_requests(
        policy
    )

    approved = approve_request(
        approvals[0],
        reviewer="security-analyst",
        reason="Containment approved.",
    )

    result = execute_policy_evaluation(
        policy,
        approvals=[approved],
    )

    assert result.simulated_count == 1
    assert result.blocked_count == 0

    assert (
        result.results[0].authorized
        is True
    )

    assert (
        result.results[0].status
        == "simulated"
    )

    print(
        "[PASS] approved request reached "
        "dry-run adapter"
    )


def test_rejected_request():
    plan = make_plan(
        request=ToolRequest(
            tool_name="block_ip",
            target="192.0.2.10",
            reason="Contain suspicious host.",
        ),
    )

    policy = evaluate_response_plan(plan)

    approvals = build_approval_requests(
        policy
    )

    rejected = reject_request(
        approvals[0],
        reviewer="security-analyst",
        reason="Insufficient evidence.",
    )

    result = execute_policy_evaluation(
        policy,
        approvals=[rejected],
    )

    assert result.simulated_count == 0
    assert result.blocked_count == 1

    print(
        "[PASS] rejected approval blocked"
    )


def test_policy_deny():
    plan = make_plan(
        request=ToolRequest(
            tool_name="block_ip",
            target="192.0.2.10",
            reason="Contain suspicious host.",
        ),
        requires_human_review=True,
    )

    policy = evaluate_response_plan(plan)

    assert (
        policy.results[0].decision
        == "DENY"
    )

    result = execute_policy_evaluation(
        policy,
        approvals=[],
    )

    assert result.blocked_count == 1
    assert result.simulated_count == 0

    print(
        "[PASS] DENY request blocked"
    )


def main():
    test_allow()
    test_pending_approval()
    test_approved_request()
    test_rejected_request()
    test_policy_deny()

    print(
        "\nTool Broker evaluation PASSED"
    )


if __name__ == "__main__":
    main()