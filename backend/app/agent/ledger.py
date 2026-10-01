from datetime import (
    datetime,
    timedelta,
)
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.investigation_event import (
    InvestigationEvent,
)
from app.models.investigation_run import (
    InvestigationRun,
)
from app.schemas.investigation_ledger import (
    InvestigationEventRecord,
    InvestigationRunListItem,
    InvestigationRunRecord,
    InvestigationTrace,
)


def start_investigation_run(
    db: Session,
    finding_id: int,
) -> InvestigationRunRecord:
    """
    Create a new auditable investigation run.
    """

    run = InvestigationRun(
        finding_id=finding_id,
        status="running",
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    return InvestigationRunRecord.model_validate(
        run
    )


def record_investigation_event(
    db: Session,
    *,
    run_id: int,
    event_type: str,
    node_name: str | None = None,
    status: str = "completed",
    summary: str | None = None,
    event_metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> InvestigationEventRecord:
    """
    Append one immutable-style audit event to the ledger.
    """

    run = db.get(
        InvestigationRun,
        run_id,
    )

    if run is None:
        raise ValueError(
            f"Investigation run not found: {run_id}"
        )

    event = InvestigationEvent(
        run_id=run_id,
        event_type=event_type,
        node_name=node_name,
        status=status,
        summary=summary,
        event_metadata=event_metadata,
    )

    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    else:
        db.flush()

    return InvestigationEventRecord.model_validate(
        event
    )


def complete_investigation_run(
    db: Session,
    *,
    run_id: int,
    final_verdict: str,
) -> InvestigationRunRecord:
    """
    Mark an investigation run as successfully completed.
    """

    run = db.get(
        InvestigationRun,
        run_id,
    )

    if run is None:
        raise ValueError(
            f"Investigation run not found: {run_id}"
        )

    run.status = "completed"
    run.final_verdict = final_verdict
    run.finished_at = datetime.utcnow()

    db.commit()
    db.refresh(run)

    return InvestigationRunRecord.model_validate(
        run
    )


def fail_investigation_run(
    db: Session,
    *,
    run_id: int,
    error_message: str,
) -> InvestigationRunRecord:
    """
    Mark an investigation run as failed.
    """

    run = db.get(
        InvestigationRun,
        run_id,
    )

    if run is None:
        raise ValueError(
            f"Investigation run not found: {run_id}"
        )

    run.status = "failed"
    run.error_message = error_message
    run.finished_at = datetime.utcnow()

    db.commit()
    db.refresh(run)

    return InvestigationRunRecord.model_validate(
        run
    )

def list_investigation_runs(
    db: Session,
    *,
    limit: int = 100,
) -> list[InvestigationRunListItem]:
    """
    List recent investigation runs with event counts.
    """

    runs = (
        db.query(InvestigationRun)
        .order_by(
            InvestigationRun.id.desc()
        )
        .limit(limit)
        .all()
    )

    if not runs:
        return []

    run_ids = [
        run.id
        for run in runs
    ]

    event_counts = dict(
        db.query(
            InvestigationEvent.run_id,
            func.count(
                InvestigationEvent.id
            ),
        )
        .filter(
            InvestigationEvent.run_id.in_(
                run_ids
            )
        )
        .group_by(
            InvestigationEvent.run_id
        )
        .all()
    )

    results = []

    for run in runs:
        record = (
            InvestigationRunRecord
            .model_validate(run)
        )

        results.append(
            InvestigationRunListItem(
                **record.model_dump(),
                event_count=event_counts.get(
                    run.id,
                    0,
                ),
            )
        )

    return results

def get_investigation_trace(
    db: Session,
    run_id: int,
) -> InvestigationTrace:
    """
    Load the complete ordered audit trace.
    """

    run = db.get(
        InvestigationRun,
        run_id,
    )

    if run is None:
        raise ValueError(
            f"Investigation run not found: {run_id}"
        )

    events = (
        db.query(InvestigationEvent)
        .filter(
            InvestigationEvent.run_id
            == run_id
        )
        .order_by(
            InvestigationEvent.id.asc()
        )
        .all()
    )

    return InvestigationTrace(
        run=InvestigationRunRecord.model_validate(
            run
        ),
        events=[
            InvestigationEventRecord.model_validate(
                event
            )
            for event in events
        ],
    )
def recover_stale_investigation_runs(
    db: Session,
    *,
    older_than_minutes: int = 30,
) -> list[InvestigationRunRecord]:
    """
    Recover abandoned InvestigationRuns that were
    left in a running state after an interrupted
    process or development restart.

    Safety conditions:

    1. Run is still marked as running.
    2. Run is older than the configured threshold.
    3. Run has no persisted investigation events.

    Existing audit history is never deleted.
    """

    if older_than_minutes <= 0:
        raise ValueError(
            "older_than_minutes must be greater than 0."
        )

    cutoff = (
        datetime.utcnow()
        - timedelta(
            minutes=older_than_minutes
        )
    )

    candidates = (
        db.query(
            InvestigationRun
        )
        .filter(
            InvestigationRun.status
            == "running",
            InvestigationRun.started_at
            < cutoff,
        )
        .order_by(
            InvestigationRun.id.asc()
        )
        .all()
    )

    recovered: list[
        InvestigationRunRecord
    ] = []

    for run in candidates:
        existing_event = (
            db.query(
                InvestigationEvent.id
            )
            .filter(
                InvestigationEvent.run_id
                == run.id
            )
            .first()
        )

        # A run with audit activity may simply be a
        # long-running investigation. Leave it alone.
        if existing_event is not None:
            continue

        # Refresh immediately before mutation in case
        # another worker completed the run.
        db.refresh(
            run
        )

        if run.status != "running":
            continue

        error_message = (
            "Stale investigation recovered after "
            "interrupted execution."
        )

        recovery_event = (
            InvestigationEvent(
                run_id=run.id,
                event_type=(
                    "stale_run_recovered"
                ),
                node_name=(
                    "stale_run_recovery"
                ),
                status="failed",
                summary=error_message,
                event_metadata={
                    "previous_status": (
                        "running"
                    ),
                    "recovery_threshold_minutes": (
                        older_than_minutes
                    ),
                    "started_at": (
                        run.started_at.isoformat()
                    ),
                },
            )
        )

        run.status = "failed"
        run.error_message = (
            error_message
        )
        run.finished_at = (
            datetime.utcnow()
        )

        db.add(
            recovery_event
        )

        db.commit()
        db.refresh(
            run
        )

        recovered.append(
            InvestigationRunRecord.model_validate(
                run
            )
        )

    return recovered

def find_tool_execution_binding(
    db: Session,
    *,
    run_id: int,
    idempotency_key: str,
) -> InvestigationEventRecord | None:
    """
    Find the most recent persisted execution attempt
    bound to one idempotency key.

    Successful, replayed, and failed executions all bind
    the execution slot to the original request fingerprint.

    Authorization/validation blocks do not bind a slot
    because they never reached Execution Intent.
    """

    events = (
        db.query(
            InvestigationEvent
        )
        .filter(
            InvestigationEvent.run_id
            == run_id,
            InvestigationEvent.event_type.in_(
                [
                    "tool_execution_simulated",
                    "tool_execution_replayed",
                    "tool_execution_failed",
                ]
            ),
        )
        .order_by(
            InvestigationEvent.id.desc()
        )
        .all()
    )

    for event in events:
        metadata = (
            event.event_metadata
            or {}
        )

        if (
            metadata.get(
                "idempotency_key"
            )
            == idempotency_key
        ):
            return (
                InvestigationEventRecord
                .model_validate(event)
            )

    return None

def find_successful_tool_execution(
    db: Session,
    *,
    run_id: int,
    idempotency_key: str,
) -> InvestigationEventRecord | None:
    """
    Find the most recent successful non-replayed
    execution for one idempotency key.

    Failed and blocked attempts are intentionally not
    treated as successful execution receipts.
    """

    events = (
        db.query(
            InvestigationEvent
        )
        .filter(
            InvestigationEvent.run_id
            == run_id,
            InvestigationEvent.event_type
            == "tool_execution_simulated",
        )
        .order_by(
            InvestigationEvent.id.desc()
        )
        .all()
    )

    for event in events:
        metadata = (
            event.event_metadata
            or {}
        )

        if (
            metadata.get(
                "idempotency_key"
            )
            == idempotency_key
            and not metadata.get(
                "replayed",
                False,
            )
        ):
            return (
                InvestigationEventRecord
                .model_validate(
                    event
                )
            )

    return None


def count_tool_execution_attempts(
    db: Session,
    *,
    run_id: int,
    idempotency_key: str,
) -> int:
    """
    Count persisted attempts for one idempotency key.

    This provides human-readable attempt numbering.
    """

    events = (
        db.query(
            InvestigationEvent
        )
        .filter(
            InvestigationEvent.run_id
            == run_id,
            InvestigationEvent.event_type.in_(
                [
                    "tool_execution_simulated",
                    "tool_execution_replayed",
                    "tool_execution_failed",
                ]
            ),
        )
        .order_by(
            InvestigationEvent.id.asc()
        )
        .all()
    )

    count = 0

    for event in events:
        metadata = (
            event.event_metadata
            or {}
        )

        if (
            metadata.get(
                "idempotency_key"
            )
            == idempotency_key
        ):
            count += 1

    return count