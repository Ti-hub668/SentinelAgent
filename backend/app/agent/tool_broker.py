from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agent.execution_guard import (
    build_execution_intent,
    build_execution_receipt,
    build_idempotency_key,
    build_request_fingerprint,
)
from app.agent.ledger import (
    count_tool_execution_attempts,
    find_successful_tool_execution,
    find_tool_execution_binding,
    record_investigation_event,
)
from app.agent.tool_registry import (
    get_tool_definition,
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
from app.schemas.tool_capability import (
    ToolRegistryAuditMetadata,
)

def _find_matching_approval(
    policy_result: ToolPolicyResult,
    approvals: list[HumanApprovalRequest],
    *,
    finding_id: int,
) -> HumanApprovalRequest | None:
    """Bind approval to the finding, slot and validated execution semantics."""
    candidates = [
        approval for approval in approvals
        if approval.finding_id == finding_id
        and approval.request_index == policy_result.request_index
    ]
    # Conflicting records must not let an older approval win by list order.
    if len(candidates) != 1:
        return None
    approval = candidates[0]
    definition = get_tool_definition(policy_result.tool_request.tool_name)
    if definition is None:
        return None
    try:
        expected = definition.validate_parameters(policy_result.tool_request)
        approved = definition.validate_parameters(approval.tool_request)
        if build_request_fingerprint(expected) != build_request_fingerprint(approved):
            return None
    except (ValidationError, ValueError, TypeError):
        return None
    return approval


def _is_authorized(
    policy_result: ToolPolicyResult,
    approvals: list[HumanApprovalRequest],
    *,
    finding_id: int,
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
            finding_id=finding_id,
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
    approvals: list[
        HumanApprovalRequest
    ],
    db: Session | None = None,
    run_id: int | None = None,
) -> ToolExecutionResult:

    """
    Process one policy result through Tool Broker.

    All executors are mock/dry-run in Day27.
    """
    if (
        (db is None)
        != (run_id is None)
    ):
        raise ValueError(
            "db and run_id must be "
            "provided together."
        )
    definition = get_tool_definition(
        policy_result.tool_request.tool_name
    )
    registry_metadata = (
        ToolRegistryAuditMetadata(
            tool_name=definition.name,
            risk_level=definition.risk_level,
            parameter_contract=definition.parameter_schema.__name__,
        )
        if definition is not None else None
    )

    authorized, authorization_reason = (
        _is_authorized(
            policy_result,
            approvals,
            finding_id=finding_id,
        )
    )

    if not authorized:
        return ToolExecutionResult(
            finding_id=finding_id,
            registry_metadata=registry_metadata,
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

    if definition is None:
        return ToolExecutionResult(
            finding_id=finding_id,
            registry_metadata=registry_metadata,

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
                "No registered tool definition exists "
                "for "
                f"{policy_result.tool_request.tool_name}."
            ),

            output={},
        )

    try:
        validated_request = (
            definition.validate_parameters(
                policy_result.tool_request
            )
        )

    except ValidationError as exc:
        issues = "; ".join(
            (
                ".".join(
                    str(part)
                    for part
                    in error["loc"]
                )
                + ": "
                + error["msg"]
            )
            for error
            in exc.errors(
                include_url=False,
                include_input=False,
            )
        )

        return ToolExecutionResult(
            finding_id=finding_id,
            registry_metadata=registry_metadata,

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
                "Tool parameter validation failed: "
                f"{issues}"
            ),

            output={},
        )

    registry_metadata = (
        registry_metadata.model_copy(
            update={
                "validated_contract":
                definition
                .parameter_schema
                .__name__,
            }
        )
    )

    execution_intent = None

    if (
        db is not None
        and run_id is not None
    ):
        request_fingerprint = (
            build_request_fingerprint(
                validated_request
            )
        )

        idempotency_key = (
            build_idempotency_key(
                run_id=run_id,
                request_index=(
                    policy_result
                    .request_index
                ),
            )
        )

        attempt = (
            count_tool_execution_attempts(
                db,
                run_id=run_id,
                idempotency_key=(
                    idempotency_key
                ),
            )
            + 1
        )

        matching_approval = (
            _find_matching_approval(
                policy_result,
                approvals,
                finding_id=finding_id,
            )
        )

        execution_intent = (
            build_execution_intent(
                finding_id=finding_id,
                run_id=run_id,
                policy_result=(
                    policy_result
                ),
                validated_request=(
                    validated_request
                ),
                approval=(
                    matching_approval
                ),
                attempt=attempt,
                request_fingerprint=(
                    request_fingerprint
                ),
                idempotency_key=(
                    idempotency_key
                ),
            )
        )
        previous_binding = (
            find_tool_execution_binding(
                db,
                run_id=run_id,
                idempotency_key=(
                    idempotency_key
                ),
            )
        )

        if (
            previous_binding
            is not None
        ):
            previous_metadata = (
                previous_binding
                .event_metadata
                or {}
            )

            previous_fingerprint = (
                previous_metadata.get(
                    "request_fingerprint"
                )
            )

            if (
                previous_fingerprint
                != request_fingerprint
            ):
                return ToolExecutionResult(
                    finding_id=finding_id,
                    request_index=(
                        policy_result
                        .request_index
                    ),
                    tool_request=(
                        validated_request
                    ),
                    policy_decision=(
                        policy_result
                        .decision
                    ),
                    authorized=True,
                    executed=False,
                    dry_run=True,
                    status="blocked",
                    message=(
                        "Replay protection blocked "
                        "a missing or mismatched execution-slot fingerprint "
                        "mismatch."
                    ),
                    output={},
                    registry_metadata=(
                        registry_metadata
                    ),
                    execution_intent=(
                        execution_intent
                    ),
                    execution_receipt=None,
                    replayed=False,
                )
        previous_execution = (
            find_successful_tool_execution(
                db,
                run_id=run_id,
                idempotency_key=(
                    idempotency_key
                ),
            )
        )

        if (
            previous_execution
            is not None
        ):
            previous_metadata = (
                previous_execution
                .event_metadata
                or {}
            )

            previous_output = (
                previous_metadata.get(
                    "output"
                )
            )

            if not isinstance(
                previous_output,
                dict,
            ):
                previous_output = {}

            receipt = (
                build_execution_receipt(
                    intent=execution_intent,
                    outcome="replayed",
                    executor_invoked=False,
                    replayed=True,
                    original_event_id=(
                        previous_execution.id
                    ),
                )
            )

            return ToolExecutionResult(
                finding_id=finding_id,
                registry_metadata=(
                    registry_metadata
                ),
                request_index=(
                    policy_result
                    .request_index
                ),
                tool_request=(
                    validated_request
                ),
                policy_decision=(
                    policy_result
                    .decision
                ),
                authorized=True,
                executed=False,
                dry_run=True,

                # Keep legacy BrokerStatus
                # compatible.
                status="simulated",

                message=(
                    "Replay detected. "
                    "Previous successful "
                    "dry-run execution was "
                    "reused and the executor "
                    "was not invoked."
                ),

                execution_intent=(
                    execution_intent
                ),
                execution_receipt=(
                    receipt
                ),
                replayed=True,
                output=previous_output,
            )

    try:
        output = definition.executor(
            validated_request
        )

        receipt = (
            build_execution_receipt(
                intent=execution_intent,
                outcome="simulated",
                executor_invoked=True,
            )
            if execution_intent
            is not None
            else None
        )

        return ToolExecutionResult(
            finding_id=finding_id,
            registry_metadata=(
                registry_metadata
            ),
            request_index=(
                policy_result.request_index
            ),
            tool_request=(
                validated_request
            ),
            policy_decision=(
                policy_result.decision
            ),
            authorized=True,
            executed=True,
            dry_run=True,
            status="simulated",
            message=(
                "Authorized request "
                "processed by dry-run "
                "executor."
            ),
            execution_intent=(
                execution_intent
            ),
            execution_receipt=(
                receipt
            ),
            replayed=False,
            output=output,
        )

    except Exception as exc:
        receipt = (
            build_execution_receipt(
                intent=execution_intent,
                outcome="failed",
                executor_invoked=True,
            )
            if execution_intent
            is not None
            else None
        )

        return ToolExecutionResult(
            finding_id=finding_id,
            registry_metadata=(
                registry_metadata
            ),
            request_index=(
                policy_result.request_index
            ),
            tool_request=(
                validated_request
            ),
            policy_decision=(
                policy_result.decision
            ),
            authorized=True,
            executed=False,
            dry_run=True,
            status="failed",
            message=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            execution_intent=(
                execution_intent
            ),
            execution_receipt=(
                receipt
            ),
            replayed=False,
            output={},
        )

def _build_batch_result(
    *,
    finding_id: int,
    results: list[
        ToolExecutionResult
    ],
) -> ToolBrokerBatchResult:
    return ToolBrokerBatchResult(
        finding_id=finding_id,
        results=results,

        simulated_count=sum(
            (
                item.status
                == "simulated"
                and not item.replayed
            )
            for item
            in results
        ),

        replayed_count=sum(
            item.replayed
            for item
            in results
        ),

        blocked_count=sum(
            item.status
            == "blocked"
            for item
            in results
        ),

        failed_count=sum(
            item.status
            == "failed"
            for item
            in results
        ),
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

    return _build_batch_result(
        finding_id=(
            evaluation.finding_id
        ),
        results=results,
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

    # Persist each result before considering the next slot in this batch.
    # This prevents sequential duplicates, but is not a concurrent reservation.
    results = []
    for policy_result in evaluation.results:
        result = execute_policy_result(
            policy_result,
            finding_id=evaluation.finding_id,
            approvals=approvals,
            db=db,
            run_id=run_id,
        )
        if result.replayed:
            event_type = (
                "tool_execution_replayed"
            )

        elif result.status == "simulated":
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
                "tool_registry": (
                    result.registry_metadata.model_dump(mode="json")
                    if result.registry_metadata is not None else None
                ),
                "execution_result":
                    result.model_dump(
                        mode="json"
                    ),
                "execution_id": (
                    result.execution_intent
                    .execution_id
                    if result.execution_intent
                    is not None
                    else None
                ),

                "request_fingerprint": (
                    result.execution_intent
                    .request_fingerprint
                    if result.execution_intent
                    is not None
                    else None
                ),

                "idempotency_key": (
                    result.execution_intent
                    .idempotency_key
                    if result.execution_intent
                    is not None
                    else None
                ),

                "execution_attempt": (
                    result.execution_intent
                    .attempt
                    if result.execution_intent
                    is not None
                    else None
                ),

                "replayed":
                    result.replayed,

                "execution_intent": (
                    result.execution_intent
                    .model_dump(
                        mode="json"
                    )
                    if result.execution_intent
                    is not None
                    else None
                ),

                "execution_receipt": (
                    result.execution_receipt
                    .model_dump(
                        mode="json"
                    )
                    if result.execution_receipt
                    is not None
                    else None
                ),
            },
        )

        results.append(result)

    return _build_batch_result(
        finding_id=evaluation.finding_id,
        results=results,
    )
