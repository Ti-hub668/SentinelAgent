from app.schemas.policy import (
    HumanApprovalRequest,
    PolicyEvaluationResult,
    ToolPolicyResult,
)
from app.schemas.response_plan import (
    ResponsePlan,
    ToolRequest,
)


def evaluate_tool_request(
    *,
    request_index: int,
    request: ToolRequest,
    plan: ResponsePlan,
) -> ToolPolicyResult:
    """
    Evaluate one ToolRequest using deterministic policy rules.

    No LLM is used here.
    """

    # --------------------------------------------------
    # Rule 1:
    # Response Agent must always operate in dry-run mode.
    # --------------------------------------------------

    if not plan.dry_run:
        return ToolPolicyResult(
            request_index=request_index,
            tool_request=request,
            decision="DENY",
            reason=(
                "ResponsePlan is not marked as dry-run. "
                "Execution requests are denied."
            ),
            requires_human_approval=False,
        )

    # --------------------------------------------------
    # Rule 2:
    # manual_review always becomes an approval workflow.
    # --------------------------------------------------

    if request.tool_name == "manual_review":
        return ToolPolicyResult(
            request_index=request_index,
            tool_request=request,
            decision="REQUIRE_APPROVAL",
            reason=(
                "The Response Agent explicitly requested "
                "human security review."
            ),
            requires_human_approval=True,
        )

    # --------------------------------------------------
    # Rule 3:
    # block_ip is never automatically executed.
    # --------------------------------------------------

    if request.tool_name == "block_ip":
        if plan.requires_human_review:
            return ToolPolicyResult(
                request_index=request_index,
                tool_request=request,
                decision="DENY",
                reason=(
                    "Network containment is denied because "
                    "the investigation still requires "
                    "human review."
                ),
                requires_human_approval=False,
            )

        return ToolPolicyResult(
            request_index=request_index,
            tool_request=request,
            decision="REQUIRE_APPROVAL",
            reason=(
                "Blocking a network target is a disruptive "
                "security action and requires explicit "
                "human approval."
            ),
            requires_human_approval=True,
        )

    # --------------------------------------------------
    # Rule 4:
    # During human-review-required investigations,
    # ticket / notification actions require approval.
    # --------------------------------------------------

    if plan.requires_human_review:
        if request.tool_name in {
            "create_ticket",
            "notify",
        }:
            return ToolPolicyResult(
                request_index=request_index,
                tool_request=request,
                decision="REQUIRE_APPROVAL",
                reason=(
                    "The investigation requires human "
                    "review before downstream response "
                    "actions are released."
                ),
                requires_human_approval=True,
            )

    # --------------------------------------------------
    # Rule 5:
    # Non-disruptive actions may proceed to Tool Broker.
    # --------------------------------------------------

    if request.tool_name in {
        "create_ticket",
        "notify",
    }:
        return ToolPolicyResult(
            request_index=request_index,
            tool_request=request,
            decision="ALLOW",
            reason=(
                "The action is non-disruptive and the "
                "grounded investigation does not require "
                "additional human review."
            ),
            requires_human_approval=False,
        )

    # --------------------------------------------------
    # Fail closed:
    # unknown tools are denied.
    # --------------------------------------------------

    return ToolPolicyResult(
        request_index=request_index,
        tool_request=request,
        decision="DENY",
        reason=(
            f"Unsupported tool request: "
            f"{request.tool_name}."
        ),
        requires_human_approval=False,
    )


def evaluate_response_plan(
    plan: ResponsePlan,
) -> PolicyEvaluationResult:
    """
    Evaluate all ToolRequests in one ResponsePlan.
    """

    results = [
        evaluate_tool_request(
            request_index=index,
            request=request,
            plan=plan,
        )
        for index, request in enumerate(
            plan.tool_requests
        )
    ]

    allow_count = sum(
        result.decision == "ALLOW"
        for result in results
    )

    deny_count = sum(
        result.decision == "DENY"
        for result in results
    )

    approval_count = sum(
        result.decision
        == "REQUIRE_APPROVAL"
        for result in results
    )

    return PolicyEvaluationResult(
        finding_id=plan.finding_id,
        grounded_verdict=(
            plan.grounded_verdict
        ),
        dry_run=plan.dry_run,
        results=results,
        allow_count=allow_count,
        deny_count=deny_count,
        approval_count=approval_count,
    )


def build_approval_requests(
    evaluation: PolicyEvaluationResult,
) -> list[HumanApprovalRequest]:
    """
    Convert REQUIRE_APPROVAL policy results into
    explicit human approval requests.
    """

    return [
        HumanApprovalRequest(
            finding_id=evaluation.finding_id,
            request_index=result.request_index,
            tool_request=result.tool_request,
            policy_reason=result.reason,
        )
        for result in evaluation.results
        if (
            result.decision
            == "REQUIRE_APPROVAL"
        )
    ]