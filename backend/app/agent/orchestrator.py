from sqlalchemy.orm import Session

from app.agent.investigation_runner import (
    run_investigation_with_ledger,
)
from app.agent.ledger import (
    get_investigation_trace,
)
from app.agent.response_runner import (
    resolve_approval_with_ledger,
    run_response_pipeline,
)
from app.agent.tool_broker import (
    execute_policy_evaluation_with_ledger,
)
from app.schemas.agent_workflow import (
    AgentWorkflowSummary,
)
from app.schemas.policy import (
    HumanApprovalRequest,
    PolicyEvaluationResult,
)
from app.schemas.response_plan import (
    ResponsePlan,
)
from app.schemas.tool_broker import (
    ToolBrokerBatchResult,
    ToolExecutionResult,
)


def _latest_event(
    trace,
    event_type: str,
):
    for event in reversed(
        trace.events
    ):
        if event.event_type == event_type:
            return event

    return None


def _load_response_plan(
    trace,
) -> ResponsePlan | None:
    event = _latest_event(
        trace,
        "response_planned",
    )

    if event is None:
        return None

    metadata = (
        event.event_metadata or {}
    )

    raw = metadata.get(
        "response_plan"
    )

    if not raw:
        return None

    return ResponsePlan.model_validate(
        raw
    )


def _load_policy_evaluation(
    trace,
) -> PolicyEvaluationResult | None:
    event = _latest_event(
        trace,
        "policy_evaluated",
    )

    if event is None:
        return None

    metadata = (
        event.event_metadata or {}
    )

    raw = metadata.get(
        "policy_evaluation"
    )

    if not raw:
        return None

    return (
        PolicyEvaluationResult
        .model_validate(raw)
    )


def _load_approvals(
    trace,
) -> list[HumanApprovalRequest]:
    """
    Reconstruct latest approval state for
    every request_index from Ledger.
    """

    approvals: dict[
        int,
        HumanApprovalRequest,
    ] = {}

    for event in trace.events:
        if event.event_type not in {
            "approval_requested",
            "approval_resolved",
        }:
            continue

        metadata = (
            event.event_metadata
            or {}
        )

        raw = metadata.get(
            "approval"
        )

        if not raw:
            continue

        approval = (
            HumanApprovalRequest
            .model_validate(raw)
        )

        approvals[
            approval.request_index
        ] = approval

    return [
        approvals[index]
        for index
        in sorted(approvals)
    ]


def _load_tool_results(
    trace,
) -> list[ToolExecutionResult]:
    results: list[
        ToolExecutionResult
    ] = []

    for event in trace.events:
        if event.event_type not in {
            "tool_execution_simulated",
            "tool_execution_blocked",
            "tool_execution_failed",
        }:
            continue

        metadata = (
            event.event_metadata
            or {}
        )

        raw = metadata.get(
            "execution_result"
        )

        if not raw:
            continue

        results.append(
            ToolExecutionResult
            .model_validate(raw)
        )

    return results


def _determine_workflow_status(
    *,
    run_status: str,
    policy: PolicyEvaluationResult | None,
    approvals: list[HumanApprovalRequest],
    tool_results: list[ToolExecutionResult],
) -> str:
    if run_status == "failed":
        return "failed"

    if any(
        result.status == "simulated"
        for result in tool_results
    ):
        return "dry_run_executed"

    if any(
        approval.status == "pending"
        for approval in approvals
    ):
        return "awaiting_approval"

    if policy is None:
        return "investigation_completed"

    if (
        policy.results
        and all(
            result.decision == "DENY"
            for result in policy.results
        )
    ):
        return "policy_blocked"

    return "ready_for_execution"


def get_workflow_summary(
    db: Session,
    run_id: int,
) -> AgentWorkflowSummary:
    trace = get_investigation_trace(
        db,
        run_id,
    )

    response_plan = (
        _load_response_plan(trace)
    )

    policy = (
        _load_policy_evaluation(trace)
    )

    approvals = (
        _load_approvals(trace)
    )

    tool_results = (
        _load_tool_results(trace)
    )

    workflow_status = (
        _determine_workflow_status(
            run_status=trace.run.status,
            policy=policy,
            approvals=approvals,
            tool_results=tool_results,
        )
    )

    return AgentWorkflowSummary(
        run_id=trace.run.id,
        finding_id=trace.run.finding_id,
        run_status=trace.run.status,
        workflow_status=workflow_status,
        final_verdict=(
            trace.run.final_verdict
        ),
        response_plan=response_plan,
        policy_evaluation=policy,
        approvals=approvals,
        tool_results=tool_results,
        event_count=len(
            trace.events
        ),
    )


def start_agent_workflow(
    db: Session,
    finding_id: int,
) -> AgentWorkflowSummary:
    """
    Unified entry point for the complete
    SentinelAgent investigation workflow.
    """

    state, run = (
        run_investigation_with_ledger(
            db,
            finding_id,
        )
    )

    if (
        state.get("status")
        != "grounding_completed"
    ):
        return get_workflow_summary(
            db,
            run.id,
        )

    run_response_pipeline(
        db,
        run_id=run.id,
        state=state,
    )

    return get_workflow_summary(
        db,
        run.id,
    )


def resolve_workflow_approval(
    db: Session,
    *,
    run_id: int,
    request_index: int,
    approved: bool,
    reviewer: str,
    reason: str,
) -> AgentWorkflowSummary:
    summary = get_workflow_summary(
        db,
        run_id,
    )

    approval = next(
        (
            item
            for item
            in summary.approvals
            if (
                item.request_index
                == request_index
            )
        ),
        None,
    )

    if approval is None:
        raise ValueError(
            "Approval request not found: "
            f"run_id={run_id}, "
            f"request_index={request_index}"
        )

    if approval.status != "pending":
        raise ValueError(
            "Approval request has already "
            f"been resolved: {approval.status}"
        )

    resolve_approval_with_ledger(
        db,
        run_id=run_id,
        approval=approval,
        approved=approved,
        reviewer=reviewer,
        reason=reason,
    )

    return get_workflow_summary(
        db,
        run_id,
    )


def execute_workflow_tools(
    db: Session,
    *,
    run_id: int,
) -> ToolBrokerBatchResult:
    """
    Send current authorized requests through
    the Day27 dry-run Tool Broker.
    """

    summary = get_workflow_summary(
        db,
        run_id,
    )

    if (
        summary.policy_evaluation
        is None
    ):
        raise ValueError(
            "Policy evaluation not found "
            f"for run {run_id}."
        )

    return (
        execute_policy_evaluation_with_ledger(
            db,
            run_id=run_id,
            evaluation=(
                summary.policy_evaluation
            ),
            approvals=summary.approvals,
        )
    )