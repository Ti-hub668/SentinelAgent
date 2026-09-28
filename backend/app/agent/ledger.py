from datetime import datetime
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
    db.commit()
    db.refresh(event)

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