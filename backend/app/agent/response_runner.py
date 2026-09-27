from sqlalchemy.orm import Session

from app.agent.approval import (
    approve_request,
    reject_request,
)
from app.agent.ledger import (
    record_investigation_event,
)
from app.agent.policy_engine import (
    build_approval_requests,
    evaluate_response_plan,
)
from app.agent.response_agent import (
    generate_response_plan,
)
from app.agent.state import (
    SentinelInvestigationState,
)
from app.schemas.policy import (
    HumanApprovalRequest,
    PolicyEvaluationResult,
)
from app.schemas.response_plan import (
    ResponsePlan,
)


def run_response_pipeline(
    db: Session,
    *,
    run_id: int,
    state: SentinelInvestigationState,
) -> tuple[
    ResponsePlan,
    PolicyEvaluationResult,
    list[HumanApprovalRequest],
]:
    """
    Run the post-investigation response pipeline.

    This function:
    1. Generates a dry-run response plan.
    2. Evaluates all tool requests using Policy Engine.
    3. Creates pending human approval requests.
    4. Writes response/policy/approval events to Ledger.

    It NEVER executes a security tool.
    """

    if state.get("status") != "grounding_completed":
        raise RuntimeError(
            "Response pipeline requires a completed "
            "grounded investigation."
        )

    # --------------------------------------------------
    # 1. Response planning
    # --------------------------------------------------

    plan = generate_response_plan(
        state
    )

    if not plan.dry_run:
        raise RuntimeError(
            "Response Agent produced a non-dry-run plan."
        )

    record_investigation_event(
        db,
        run_id=run_id,
        event_type="response_planned",
        node_name="response_agent",
        status="completed",
        summary=(
            f"Generated dry-run response plan with "
            f"{len(plan.tool_requests)} tool request(s)."
        ),
        event_metadata={
            "finding_id": plan.finding_id,
            "grounded_verdict":
                plan.grounded_verdict,
            "decision_action":
                plan.decision_action,
            "priority":
                plan.priority,
            "requires_human_review":
                plan.requires_human_review,
            "dry_run":
                plan.dry_run,
            "response_plan":
                plan.model_dump(),
            "tool_requests": [
                request.model_dump()
                for request
                in plan.tool_requests
            ],
        },
    )

    # --------------------------------------------------
    # 2. Deterministic policy evaluation
    # --------------------------------------------------

    evaluation = evaluate_response_plan(
        plan
    )

    record_investigation_event(
        db,
        run_id=run_id,
        event_type="policy_evaluated",
        node_name="policy_engine",
        status="completed",
        summary=(
            "Policy Engine evaluated "
            f"{len(evaluation.results)} request(s): "
            f"{evaluation.allow_count} allowed, "
            f"{evaluation.deny_count} denied, "
            f"{evaluation.approval_count} requiring "
            "approval."
        ),
        event_metadata={
            "allow_count":
                evaluation.allow_count,
            "deny_count":
                evaluation.deny_count,
            "approval_count":
                evaluation.approval_count,
            "policy_evaluation":
                evaluation.model_dump(),
            "results": [
                result.model_dump()
                for result
                in evaluation.results
            ],
        },
    )

    # --------------------------------------------------
    # 3. Build pending human approvals
    # --------------------------------------------------

    approvals = build_approval_requests(
        evaluation
    )

    for approval in approvals:
        record_investigation_event(
            db,
            run_id=run_id,
            event_type="approval_requested",
            node_name="human_approval",
            status="completed",
            summary=(
                "Human approval requested for "
                f"{approval.tool_request.tool_name}."
            ),
            event_metadata={
                "finding_id":
                    approval.finding_id,
                "request_index":
                    approval.request_index,
                "tool_request":
                    approval.tool_request.model_dump(),
                "policy_reason":
                    approval.policy_reason,
                "approval_status":
                    approval.status,
                "approval":
                    approval.model_dump(),
            },
        )

    return (
        plan,
        evaluation,
        approvals,
    )


def resolve_approval_with_ledger(
    db: Session,
    *,
    run_id: int,
    approval: HumanApprovalRequest,
    approved: bool,
    reviewer: str,
    reason: str,
) -> HumanApprovalRequest:
    """
    Explicitly resolve a HumanApprovalRequest and
    persist the resolution to Investigation Ledger.

    Approval does NOT execute the requested tool.
    """

    if approved:
        resolved = approve_request(
            approval,
            reviewer=reviewer,
            reason=reason,
        )
    else:
        resolved = reject_request(
            approval,
            reviewer=reviewer,
            reason=reason,
        )

    record_investigation_event(
        db,
        run_id=run_id,
        event_type="approval_resolved",
        node_name="human_approval",
        status="completed",
        summary=(
            f"Human approval for "
            f"{resolved.tool_request.tool_name} "
            f"was {resolved.status}."
        ),
        event_metadata={
            "finding_id":
                resolved.finding_id,
            "request_index":
                resolved.request_index,
            "tool_request":
                resolved.tool_request.model_dump(),
            "policy_reason":
                resolved.policy_reason,
            "approval_status":
                resolved.status,
            "approval":
                resolved.model_dump(),
            "reviewer":
                resolved.reviewer,
            "review_reason":
                resolved.review_reason,
        },
    )

    return resolved