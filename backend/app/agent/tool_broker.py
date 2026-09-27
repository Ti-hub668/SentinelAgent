from sqlalchemy.orm import Session

from app.agent.executors.mock_executors import (
    simulate_block_ip,
    simulate_create_ticket,
    simulate_manual_review,
    simulate_notify,
)
from app.agent.ledger import (
    record_investigation_event,
)
from app.schemas.policy import (
    HumanApprovalRequest,
    PolicyEvaluationResult,
    ToolPolicyResult,
)
from app.schemas.tool_broker import (
    ToolBrokerBatchResult,
    ToolExecutionResult,
)


MOCK_EXECUTORS = {
    "create_ticket": simulate_create_ticket,
    "notify": simulate_notify,
    "block_ip": simulate_block_ip,
    "manual_review": simulate_manual_review,
}


def _find_matching_approval(
    policy_result: ToolPolicyResult,
    approvals: list[HumanApprovalRequest],
) -> HumanApprovalRequest | None:
    """
    Find approval corresponding to one policy request.
    """

    for approval in approvals:
        if (
            approval.request_index
            == policy_result.request_index
            and approval.tool_request.tool_name
            == policy_result.tool_request.tool_name
            and approval.tool_request.target
            == policy_result.tool_request.target
        ):
            return approval

    return None


def _is_authorized(
    policy_result: ToolPolicyResult,
    approvals: list[HumanApprovalRequest],
) -> tuple[bool, str]:
    """
    Validate whether a ToolRequest may reach an executor.

    Policy Engine owns policy decisions.
    Tool Broker only verifies authorization.
    """

    if policy_result.decision == "DENY":
        return (
            False,
            "Policy Engine explicitly denied the request.",
        )

    if policy_result.decision == "ALLOW":
        return (
            True,
            "Policy Engine allowed the request.",
        )

    if (
        policy_result.decision
        == "REQUIRE_APPROVAL"
    ):
        approval = _find_matching_approval(
            policy_result,
            approvals,
        )

        if approval is None:
            return (
                False,
                "Required human approval was not found.",
            )

        if approval.status == "pending":
            return (
                False,
                "Human approval is still pending.",
            )

        if approval.status == "rejected":
            return (
                False,
                "Human approval was rejected.",
            )

        if approval.status == "approved":
            return (
                True,
                "Human approval was granted.",
            )

        return (
            False,
            "Unknown approval status.",
        )

    return (
        False,
        "Unknown policy decision.",
    )


def execute_policy_result(
    policy_result: ToolPolicyResult,
    *,
    finding_id: int,
    approvals: list[HumanApprovalRequest],
) -> ToolExecutionResult:
    """
    Process one policy result through Tool Broker.

    All executors are mock/dry-run in Day27.
    """

    authorized, authorization_reason = (
        _is_authorized(
            policy_result,
            approvals,
        )
    )

    if not authorized:
        return ToolExecutionResult(
            finding_id=finding_id,
            request_index=(
                policy_result.request_index
            ),
            tool_request=(
                policy_result.tool_request
            ),
            policy_decision=(
                policy_result.decision
            ),
            authorized=False,
            executed=False,
            dry_run=True,
            status="blocked",
            message=authorization_reason,
            output={},
        )

    executor = MOCK_EXECUTORS.get(
        policy_result.tool_request.tool_name
    )

    if executor is None:
        return ToolExecutionResult(
            finding_id=finding_id,
            request_index=(
                policy_result.request_index
            ),
            tool_request=(
                policy_result.tool_request
            ),
            policy_decision=(
                policy_result.decision
            ),
            authorized=False,
            executed=False,
            dry_run=True,
            status="blocked",
            message=(
                "No registered executor exists for "
                f"{policy_result.tool_request.tool_name}."
            ),
            output={},
        )

    try:
        output = executor(
            policy_result.tool_request
        )

        return ToolExecutionResult(
            finding_id=finding_id,
            request_index=(
                policy_result.request_index
            ),
            tool_request=(
                policy_result.tool_request
            ),
            policy_decision=(
                policy_result.decision
            ),
            authorized=True,

            # The mock executor did run, but no
            # real-world side effect occurred.
            executed=True,
            dry_run=True,
            status="simulated",
            message=(
                "Authorized request processed by "
                "dry-run executor."
            ),
            output=output,
        )

    except Exception as exc:
        return ToolExecutionResult(
            finding_id=finding_id,
            request_index=(
                policy_result.request_index
            ),
            tool_request=(
                policy_result.tool_request
            ),
            policy_decision=(
                policy_result.decision
            ),
            authorized=True,
            executed=False,
            dry_run=True,
            status="failed",
            message=(
                f"{type(exc).__name__}: {exc}"
            ),
            output={},
        )


def execute_policy_evaluation(
    evaluation: PolicyEvaluationResult,
    *,
    approvals: list[HumanApprovalRequest],
) -> ToolBrokerBatchResult:
    """
    Process every policy result.

    No real-world tools are executed.
    """

    results = [
        execute_policy_result(
            policy_result,
            finding_id=evaluation.finding_id,
            approvals=approvals,
        )
        for policy_result
        in evaluation.results
    ]

    return ToolBrokerBatchResult(
        finding_id=evaluation.finding_id,
        results=results,
        simulated_count=sum(
            item.status == "simulated"
            for item in results
        ),
        blocked_count=sum(
            item.status == "blocked"
            for item in results
        ),
        failed_count=sum(
            item.status == "failed"
            for item in results
        ),
    )


def execute_policy_evaluation_with_ledger(
    db: Session,
    *,
    run_id: int,
    evaluation: PolicyEvaluationResult,
    approvals: list[HumanApprovalRequest],
) -> ToolBrokerBatchResult:
    """
    Execute broker workflow and persist audit events.
    """

    batch = execute_policy_evaluation(
        evaluation,
        approvals=approvals,
    )

    for result in batch.results:
        if result.status == "simulated":
            event_type = (
                "tool_execution_simulated"
            )

        elif result.status == "blocked":
            event_type = (
                "tool_execution_blocked"
            )

        else:
            event_type = (
                "tool_execution_failed"
            )

        record_investigation_event(
            db,
            run_id=run_id,
            event_type=event_type,
            node_name="tool_broker",
            status=(
                "failed"
                if result.status == "failed"
                else "completed"
            ),
            summary=(
                f"Tool Broker processed "
                f"{result.tool_request.tool_name}: "
                f"{result.status}."
            ),
            event_metadata={
                "finding_id":
                    result.finding_id,
                "request_index":
                    result.request_index,
                "tool_name":
                    result.tool_request.tool_name,
                "target":
                    result.tool_request.target,
                "policy_decision":
                    result.policy_decision,
                "authorized":
                    result.authorized,
                "executed":
                    result.executed,
                "dry_run":
                    result.dry_run,
                "broker_status":
                    result.status,
                "message":
                    result.message,
                "output":
                    result.output,
                "execution_result":
                    result.model_dump(),
            },
        )

    return batch