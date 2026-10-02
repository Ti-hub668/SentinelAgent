from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.adapters.base import (
    ToolExecutionContext,
)
from app.agent.execution_claims import (
    acquire_reconciliation_claim,
    finish_reconciled_claim,
)
from app.agent.ledger import (
    record_investigation_event,
)
from app.agent.tool_registry import (
    get_tool_definition,
)
from app.core.tool_settings import (
    redact_tool_secrets,
)
from app.models.execution_claim import (
    ExecutionClaim,
)
from app.schemas.execution import (
    ExecutionReceipt,
)


@dataclass(frozen=True)
class ReconciliationSummary:
    run_id: int
    checked: int = 0
    confirmed: int = 0
    unresolved: int = 0
    failed: int = 0


def _build_execution_context(
    claim: ExecutionClaim,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        execution_id=claim.execution_id,
        idempotency_key=claim.idempotency_key,
        request_fingerprint=(
            claim.request_fingerprint
        ),
        run_id=claim.run_id,
        request_index=claim.request_index,
        attempt=claim.attempt,
    )


def _record_unresolved(
    db: Session,
    *,
    claim: ExecutionClaim,
    state: str,
    message: str,
    output: dict | None = None,
) -> None:
    record_investigation_event(
        db,
        run_id=claim.run_id,
        event_type=(
            "tool_reconciliation_unresolved"
        ),
        node_name=(
            "reconciliation_service"
        ),
        status="failed",
        summary=message,
        event_metadata={
            "claim_id": claim.id,
            "execution_id":
                claim.execution_id,
            "tool_name":
                claim.tool_name,
            "state": state,
            "output": redact_tool_secrets(
                output or {}
            ),
        },
    )


def reconcile_run(
    db: Session,
    *,
    run_id: int,
) -> ReconciliationSummary:
    """
    Reconcile stale execution claims belonging to
    one investigation run.

    Reconciliation may inspect external state but
    must never invoke the original execution path.
    """

    claim_ids = list(
        db.scalars(
            select(
                ExecutionClaim.id
            ).where(
                ExecutionClaim.run_id
                == run_id,
                ExecutionClaim.status
                == "claimed",
            )
        ).all()
    )

    checked = 0
    confirmed = 0
    unresolved = 0
    failed = 0

    for claim_id in claim_ids:
        checked += 1

        acquisition = (
            acquire_reconciliation_claim(
                db,
                claim_id=claim_id,
            )
        )

        if acquisition.state in {
            "missing",
            "completed",
            "not_reconcilable",
            "not_stale",
            "in_progress",
        }:
            continue

        if (
            acquisition.state
            != "acquired"
            or acquisition.owner_token
            is None
        ):
            failed += 1
            continue

        claim = db.get(
            ExecutionClaim,
            claim_id,
        )

        if claim is None:
            failed += 1
            continue

        record_investigation_event(
            db,
            run_id=run_id,
            event_type=(
                "tool_reconciliation_started"
            ),
            node_name=(
                "reconciliation_service"
            ),
            status="started",
            summary=(
                "Stale execution claim entered "
                "external reconciliation."
            ),
            event_metadata={
                "claim_id": claim.id,
                "execution_id":
                    claim.execution_id,
                "tool_name":
                    claim.tool_name,
                "attempt":
                    claim.attempt,
            },
        )

        if not claim.tool_name:
            unresolved += 1

            _record_unresolved(
                db,
                claim=claim,
                state="missing_tool_name",
                message=(
                    "Execution claim has no durable "
                    "tool binding."
                ),
            )

            continue

        definition = get_tool_definition(
            claim.tool_name
        )

        if definition is None:
            unresolved += 1

            _record_unresolved(
                db,
                claim=claim,
                state=(
                    "missing_tool_definition"
                ),
                message=(
                    "No registered tool definition "
                    "exists for reconciliation."
                ),
            )

            continue

        context = _build_execution_context(
            claim
        )

        try:
            result = (
                definition.adapter.reconcile(
                    execution_context=context,
                )
            )

        except Exception:
            db.rollback()

            failed += 1

            claim = db.get(
                ExecutionClaim,
                claim_id,
            )

            if claim is not None:
                record_investigation_event(
                    db,
                    run_id=run_id,
                    event_type=(
                        "tool_reconciliation_failed"
                    ),
                    node_name=(
                        "reconciliation_service"
                    ),
                    status="failed",
                    summary=(
                        "External reconciliation "
                        "failed."
                    ),
                    event_metadata={
                        "claim_id":
                            claim.id,
                        "execution_id":
                            claim.execution_id,
                        "tool_name":
                            claim.tool_name,
                    },
                )

            continue

        safe_output = redact_tool_secrets(
            result.output
        )

        if (
            result.state
            != "confirmed_completed"
        ):
            unresolved += 1

            _record_unresolved(
                db,
                claim=claim,
                state=result.state,
                message=result.message,
                output=safe_output,
            )

            continue

        receipt = ExecutionReceipt(
            execution_id=(
                claim.execution_id
            ),
            idempotency_key=(
                claim.idempotency_key
            ),
            outcome="executed",
            executor_invoked=True,
            replayed=False,
            original_event_id=None,
            completed_at=datetime.now(
                timezone.utc
            ),
        )

        try:
            event = record_investigation_event(
                db,
                commit=False,
                run_id=run_id,
                event_type=(
                    "tool_reconciliation_confirmed"
                ),
                node_name=(
                    "reconciliation_service"
                ),
                status="completed",
                summary=result.message,
                event_metadata={
                    "claim_id": claim.id,
                    "execution_id":
                        claim.execution_id,
                    "tool_name":
                        claim.tool_name,
                    "state":
                        result.state,
                    "output":
                        safe_output,
                    "execution_receipt":
                        receipt.model_dump(
                            mode="json"
                        ),
                },
            )

            finish_reconciled_claim(
                db,
                claim_id=claim.id,
                owner_token=(
                    acquisition.owner_token
                ),
                attempt=(
                    acquisition.attempt
                ),
                receipt=receipt.model_dump(
                    mode="json"
                ),
                output=safe_output,
                event_id=event.id,
            )

            db.commit()

        except Exception:
            db.rollback()
            raise

        confirmed += 1

    return ReconciliationSummary(
        run_id=run_id,
        checked=checked,
        confirmed=confirmed,
        unresolved=unresolved,
        failed=failed,
    )