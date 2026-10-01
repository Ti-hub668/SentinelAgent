"""Unique INSERT and compare-and-swap claims; no process-local locks or leases.

These functions own transaction boundaries. Pass a session without pending writes.
Only confirmed dry-run failures may be retried, at most three attempts per slot.
An uncertain outcome stays claimed and requires operator reconciliation.
"""
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agent.ledger import (
    count_tool_execution_attempts, find_successful_tool_execution,
    find_tool_execution_binding,
)
from app.models.execution_claim import ExecutionClaim
from app.schemas.execution import ExecutionIntent

MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class ClaimDecision:
    state: str
    attempt: int
    owner_token: str | None = None
    output: dict | None = None
    event_id: int | None = None
    receipt: dict | None = None


def acquire_claim(db: Session, intent: ExecutionIntent) -> ClaimDecision:
    if db.new or db.dirty or db.deleted:
        raise ValueError("Claim acquisition requires a session without pending writes.")
    # End a caller's read snapshot, including MySQL REPEATABLE READ snapshots.
    db.rollback()
    key = intent.idempotency_key
    binding = find_tool_execution_binding(db, run_id=intent.run_id, idempotency_key=key)
    if binding and (binding.event_metadata or {}).get("request_fingerprint") != intent.request_fingerprint:
        db.rollback()
        return ClaimDecision("conflict", intent.attempt)
    legacy = find_successful_tool_execution(db, run_id=intent.run_id, idempotency_key=key)
    if legacy and (legacy.event_metadata or {}).get("request_fingerprint") != intent.request_fingerprint:
        db.rollback()
        return ClaimDecision("conflict", intent.attempt)
    previous_attempts = count_tool_execution_attempts(db, run_id=intent.run_id, idempotency_key=key)
    legacy_metadata = legacy.event_metadata or {} if legacy else {}
    token = uuid4().hex
    initial_attempt = max(1, previous_attempts + (0 if legacy else 1))
    candidate = ExecutionClaim(
        run_id=intent.run_id, request_index=intent.request_index,
        idempotency_key=key, request_fingerprint=intent.request_fingerprint,
        execution_id=intent.execution_id, owner_token=token,
        status="completed" if legacy else "claimed", attempt=initial_attempt,
        completed_at=datetime.utcnow() if legacy else None,
        receipt=legacy_metadata.get("execution_receipt"),
        output=legacy_metadata.get("output", {}) if legacy else None,
        event_id=legacy.id if legacy else None,
    )
    # Legacy retries obey the same budget. Do not create an executable claim.
    if not legacy and initial_attempt > MAX_ATTEMPTS:
        db.rollback()
        return ClaimDecision("retry_exhausted", previous_attempts)
    db.add(candidate)
    try:
        db.commit()  # Ownership is durable BEFORE returning permission to execute.
    except IntegrityError:
        db.rollback()
    else:
        decision = ClaimDecision("completed" if legacy else "acquired", initial_attempt,
                                 token if not legacy else None, candidate.output, candidate.event_id, candidate.receipt)
        db.rollback()
        return decision

    existing = db.scalar(select(ExecutionClaim).where(ExecutionClaim.idempotency_key == key))
    if existing is None:
        raise RuntimeError("Claim insertion failed without an existing slot.")
    attempt = existing.attempt
    if (existing.request_fingerprint != intent.request_fingerprint
            or existing.run_id != intent.run_id or existing.request_index != intent.request_index):
        decision = ClaimDecision("conflict", attempt)
    elif existing.status == "completed":
        decision = ClaimDecision("completed", attempt, output=existing.output, event_id=existing.event_id, receipt=existing.receipt)
    elif existing.status not in {"failed", "released"}:
        decision = ClaimDecision("in_progress", attempt)
    elif attempt >= MAX_ATTEMPTS:
        decision = ClaimDecision("retry_exhausted", attempt)
    else:
        # Exact observed version fences concurrent retry contenders, even if a
        # faster winner fails again before a delayed contender reaches UPDATE.
        observed_token, observed_status = existing.owner_token, existing.status
        db.rollback()
        changed = db.execute(update(ExecutionClaim).where(
            ExecutionClaim.idempotency_key == key,
            ExecutionClaim.request_fingerprint == intent.request_fingerprint,
            ExecutionClaim.status == observed_status,
            ExecutionClaim.attempt == attempt,
            ExecutionClaim.owner_token == observed_token,
        ).values(status="claimed", attempt=attempt + 1, owner_token=token,
                 updated_at=datetime.utcnow(), completed_at=None,
                 receipt=None, output=None, event_id=None),
            execution_options={"synchronize_session": False}).rowcount
        db.commit()
        return ClaimDecision("acquired" if changed == 1 else "in_progress",
                             attempt + 1 if changed == 1 else attempt,
                             token if changed == 1 else None)
    db.rollback()
    return decision


def finish_claim(db: Session, intent: ExecutionIntent, owner_token: str,
                 *, status: str, receipt: dict, output: dict, event_id: int) -> None:
    """Stage fenced finalization in the SAME transaction as its ledger event.

    Caller must commit; any failure must rollback both writes. Never translate a
    persistence error after executor success into a retryable executor failure.
    """
    if status not in {"completed", "failed"}:
        raise ValueError("Invalid claim final state.")
    changed = db.execute(update(ExecutionClaim).where(
        ExecutionClaim.idempotency_key == intent.idempotency_key,
        ExecutionClaim.request_fingerprint == intent.request_fingerprint,
        ExecutionClaim.status == "claimed",
        ExecutionClaim.owner_token == owner_token,
        ExecutionClaim.attempt == intent.attempt,
    ).values(status=status, receipt=receipt, output=output, event_id=event_id,
             updated_at=datetime.utcnow(),
             completed_at=datetime.utcnow() if status == "completed" else None),
        execution_options={"synchronize_session": False}).rowcount
    if changed != 1:
        raise RuntimeError("Execution claim ownership lost; completion rejected.")
