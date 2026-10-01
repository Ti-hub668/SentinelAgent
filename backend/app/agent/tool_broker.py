from app.core.tool_settings import external_tool_execution_enabled, get_github_ticket_settings, redact_tool_secrets
from sqlalchemy import select
from app.models.execution_claim import ExecutionClaim
from app.models.investigation_run import InvestigationRun
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agent.execution_claims import acquire_claim, finish_claim
from app.agent.execution_guard import (
    build_execution_intent,
    build_execution_receipt,
    build_idempotency_key,
    build_request_fingerprint,
)
from app.agent.ledger import (
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
from app.agent.adapters.base import (
    ToolExecutionContext,
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

    Default to dry-run; external execution requires an explicit durable gate.
    """
    if (
        (db is None)
        != (run_id is None)
    ):
        raise ValueError(
            "db and run_id must be "
            "provided together."
        )
    safe_request = policy_result.tool_request.model_copy(update={
        key: redact_tool_secrets(value) for key, value in policy_result.tool_request.model_dump().items()
    })
    policy_result = policy_result.model_copy(update={"tool_request": safe_request})
    approvals = [approval.model_copy(update={"reviewer": redact_tool_secrets(approval.reviewer)}) for approval in approvals]
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

    real_requested = external_tool_execution_enabled()
    dry_run = not real_requested
    gate_error = None
    if real_requested:
        if definition.name != "create_ticket":
            gate_error = "External execution is only permitted for create_ticket."
        elif db is None or run_id is None:
            gate_error = "External execution requires db, run_id and a durable claim."
        elif db.get(InvestigationRun, run_id) is None:
            gate_error = "External execution requires an existing investigation run."
        else:
            completed = db.scalar(select(ExecutionClaim).where(
                ExecutionClaim.idempotency_key == build_idempotency_key(
                    run_id=run_id, request_index=policy_result.request_index),
                ExecutionClaim.status == "completed",
            ))
            try:
                if completed is None and not get_github_ticket_settings().configured:
                    gate_error = "GitHub ticket integration is not enabled/configured."
            except (ValueError, TypeError):
                gate_error = "GitHub ticket configuration is invalid."
    if gate_error:
        return ToolExecutionResult(
            finding_id=finding_id, request_index=policy_result.request_index,
            tool_request=validated_request, policy_decision=policy_result.decision,
            authorized=True, executed=False, dry_run=dry_run, status="blocked",
            registry_metadata=registry_metadata, message=gate_error, output={},
        )

    execution_intent = None
    claim = None
    common = dict(
        finding_id=finding_id, request_index=policy_result.request_index,
        tool_request=validated_request, policy_decision=policy_result.decision,
        authorized=True, dry_run=dry_run, registry_metadata=registry_metadata,
    )
    if db is not None:
        execution_intent = build_execution_intent(
            finding_id=finding_id, run_id=run_id, policy_result=policy_result,
            validated_request=validated_request,
            approval=_find_matching_approval(policy_result, approvals, finding_id=finding_id),
            attempt=1, request_fingerprint=build_request_fingerprint(validated_request),
            idempotency_key=build_idempotency_key(
                run_id=run_id, request_index=policy_result.request_index),
        )
        claim = acquire_claim(db, execution_intent)
        execution_intent = execution_intent.model_copy(update={"attempt": claim.attempt})
        common["execution_intent"] = execution_intent
        if claim.state == "completed":
            original_status = "executed" if (claim.receipt or {}).get("outcome") == "executed" else "simulated"
            common["dry_run"] = original_status == "simulated"
            return ToolExecutionResult(
                **common, executed=False, status=original_status, replayed=True,
                message="Replay detected; durable completed claim reused without adapter invocation.",
                output=redact_tool_secrets(claim.output or {}),
                execution_receipt=build_execution_receipt(
                    intent=execution_intent, outcome="replayed", executor_invoked=False,
                    replayed=True, original_event_id=claim.event_id),
            )
        if claim.state != "acquired":
            messages = {
                "conflict": "Execution-slot fingerprint conflict; request blocked.",
                "in_progress": "Execution claim in_progress; retry cannot invoke adapter.",
                "retry_exhausted": "Execution retry budget exhausted; operator review required.",
            }
            return ToolExecutionResult(**common, executed=False, status="blocked",
                                       message=messages[claim.state], output={})

    # The adapter boundary remains isolated here.
    # Every persistent/API execution reaches here only after durable ownership.
    try:
        adapter_context = None

        if execution_intent is not None:
            adapter_context = ToolExecutionContext(
                execution_id=execution_intent.execution_id,
                idempotency_key=execution_intent.idempotency_key,
                request_fingerprint=(
                    execution_intent.request_fingerprint
                ),
                run_id=execution_intent.run_id,
                request_index=execution_intent.request_index,
                attempt=execution_intent.attempt,
            )

        output = definition.adapter.execute(
            parameters=validated_request.parameters,
            dry_run=dry_run,
            execution_context=adapter_context,
        )
    except Exception:
        result = ToolExecutionResult(
            **common, executed=False, status="failed",
            message="Tool adapter execution failed; external details suppressed.", output={},
            execution_receipt=build_execution_receipt(
                intent=execution_intent, outcome="failed", executor_invoked=True,
            ) if execution_intent else None,
        )
    else:
        # Validation/serialization/persistence errors after the call are NOT
        # evidence that side effects failed. Leave ownership claimed on error.
        result = ToolExecutionResult(
            **common, executed=True, status="simulated" if dry_run else "executed",
            message="Authorized request processed by dry-run executor." if dry_run else "Authorized GitHub ticket execution completed.", output=redact_tool_secrets(output),
            execution_receipt=build_execution_receipt(
                intent=execution_intent, outcome="simulated" if dry_run else "executed", executor_invoked=True,
            ) if execution_intent else None,
        )
    if claim is not None:
        try:
            event = _record_tool_result(db, run_id=run_id, result=result, commit=False)
            finish_claim(
                db, execution_intent, claim.owner_token,
                status="completed" if result.executed else "failed",
                receipt=result.execution_receipt.model_dump(mode="json"),
                output=result.output, event_id=event.id,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
    return result


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

        executed_count=sum(item.status == "executed" and not item.replayed for item in results),
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

    Without a Ledger, an enabled real-mode gate blocks execution.
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

    # Durable claim acquisition serializes concurrent execution of each slot.
    results = []
    for policy_result in evaluation.results:
        result = execute_policy_result(
            policy_result,
            finding_id=evaluation.finding_id,
            approvals=approvals,
            db=db,
            run_id=run_id,
        )
        # Executor outcomes were already committed atomically with their claim.
        if result.execution_receipt is None or not result.execution_receipt.executor_invoked:
            _record_tool_result(db, run_id=run_id, result=result)

        results.append(result)

    return _build_batch_result(
        finding_id=evaluation.finding_id,
        results=results,
    )


def _record_tool_result(db, *, run_id, result, commit=True):
    if result.replayed:
        event_type = (
            "tool_execution_replayed"
        )

    elif result.status == "executed":
        event_type = "tool_execution_executed"

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

    return record_investigation_event(
        db,
        commit=commit,
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
