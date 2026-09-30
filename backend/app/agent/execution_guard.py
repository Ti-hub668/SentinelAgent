import hashlib
import json
from datetime import (
    datetime,
    timezone,
)

from app.schemas.execution import (
    ExecutionAuthorizationSnapshot,
    ExecutionIntent,
    ExecutionReceipt,
)
from app.schemas.policy import (
    HumanApprovalRequest,
    ToolPolicyResult,
)
from app.schemas.response_plan import (
    ToolRequest,
)


def _canonical_json(
    payload: dict,
) -> str:
    """
    Produce deterministic JSON suitable for
    cryptographic request fingerprints.
    """

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def build_request_fingerprint(
    request: ToolRequest,
) -> str:
    """
    Fingerprint execution semantics only.

    reason is intentionally excluded because it is
    explanatory text and must not allow an LLM wording
    change to bypass replay protection.
    """

    payload = {
        "tool_name":
            request.tool_name,
        "target":
            request.target,
        "parameters":
            request.parameters,
    }

    return (
        "req_"
        + _sha256(
            _canonical_json(
                payload
            )
        )
    )


def build_idempotency_key(
    *,
    run_id: int,
    request_index: int,
) -> str:
    """
    Build a stable execution-slot identity.

    The key identifies one ToolRequest position inside
    one investigation run. Request semantics are tracked
    separately by request_fingerprint.

    Therefore:
    - same run + same request_index -> same key
    - different run -> different key
    """

    payload = {
        "run_id":
            run_id,
        "request_index":
            request_index,
    }

    return (
        "idem_"
        + _sha256(
            _canonical_json(
                payload
            )
        )
    )


def build_execution_id(
    idempotency_key: str,
) -> str:
    """
    Stable execution identity for one idempotent action.
    """

    digest = _sha256(
        idempotency_key
    )

    return (
        f"exec_{digest[:32]}"
    )


def build_authorization_snapshot(
    *,
    policy_result: ToolPolicyResult,
    approval: (
        HumanApprovalRequest
        | None
    ),
) -> ExecutionAuthorizationSnapshot:
    if (
        policy_result.decision
        != "REQUIRE_APPROVAL"
    ):
        status = "not_required"

    elif approval is None:
        status = "missing"

    elif approval.status in {
        "pending",
        "approved",
        "rejected",
    }:
        status = approval.status

    else:
        status = "unknown"

    return ExecutionAuthorizationSnapshot(
        policy_decision=(
            policy_result.decision
        ),
        approval_required=(
            policy_result.decision
            == "REQUIRE_APPROVAL"
        ),
        approval_status=status,
        reviewer=(
            approval.reviewer
            if approval is not None
            else None
        ),
    )


def build_execution_intent(
    *,
    finding_id: int,
    run_id: int,
    policy_result: ToolPolicyResult,
    validated_request: ToolRequest,
    approval: (
        HumanApprovalRequest
        | None
    ),
    attempt: int,
    request_fingerprint: str,
    idempotency_key: str,
) -> ExecutionIntent:
    return ExecutionIntent(
        execution_id=(
            build_execution_id(
                idempotency_key
            )
        ),
        finding_id=finding_id,
        run_id=run_id,
        request_index=(
            policy_result.request_index
        ),
        tool_name=(
            validated_request.tool_name
        ),
        target=(
            validated_request.target
        ),
        request_fingerprint=(
            request_fingerprint
        ),
        idempotency_key=(
            idempotency_key
        ),
        authorization=(
            build_authorization_snapshot(
                policy_result=(
                    policy_result
                ),
                approval=approval,
            )
        ),
        attempt=attempt,
        created_at=(
            datetime.now(
                timezone.utc
            )
        ),
    )


def build_execution_receipt(
    *,
    intent: ExecutionIntent,
    outcome: str,
    executor_invoked: bool,
    replayed: bool = False,
    original_event_id: (
        int | None
    ) = None,
) -> ExecutionReceipt:
    return ExecutionReceipt(
        execution_id=(
            intent.execution_id
        ),
        idempotency_key=(
            intent.idempotency_key
        ),
        outcome=outcome,
        executor_invoked=(
            executor_invoked
        ),
        replayed=replayed,
        original_event_id=(
            original_event_id
        ),
        completed_at=(
            datetime.now(
                timezone.utc
            )
        ),
    )