"""Day46 stale execution-claim detection checks."""

import os
from datetime import (
    datetime,
    timedelta,
)
from unittest.mock import patch

from sqlalchemy import (
    create_engine,
    select,
)
from sqlalchemy.orm import Session

from app.agent.execution_claims import (
    acquire_claim,
)
from app.agent.ledger import (
    start_investigation_run,
)
from app.models.execution_claim import (
    ExecutionClaim,
)
from app.models.investigation_event import (
    InvestigationEvent,
)
from app.models.investigation_run import (
    InvestigationRun,
)
from app.schemas.execution import (
    ExecutionAuthorizationSnapshot,
    ExecutionIntent,
)


def make_intent(
    *,
    run_id: int,
) -> ExecutionIntent:
    return ExecutionIntent(
        execution_id=(
            "exec-day46-stale-001"
        ),
        finding_id=62,
        run_id=run_id,
        request_index=0,
        tool_name="create_ticket",
        target="finding:62",
        request_fingerprint=(
            "fingerprint-day46-stale"
        ),
        idempotency_key=(
            "idempotency-day46-stale"
        ),
        authorization=(
            ExecutionAuthorizationSnapshot(
                policy_decision="ALLOW",
                approval_required=False,
                approval_status=(
                    "not_required"
                ),
            )
        ),
        attempt=1,
        created_at=datetime.utcnow(),
    )


def build_database():
    engine = create_engine(
        "sqlite:///:memory:"
    )

    InvestigationRun.__table__.create(
        engine
    )

    InvestigationEvent.__table__.create(
        engine
    )

    ExecutionClaim.__table__.create(
        engine
    )

    return engine


def test_fresh_claim_remains_in_progress():
    engine = build_database()

    try:
        with Session(
            engine
        ) as db:
            run = (
                start_investigation_run(
                    db,
                    62,
                )
            )

            intent = make_intent(
                run_id=run.id
            )

            with patch.dict(
                os.environ,
                {
                    "SENTINEL_EXECUTION_"
                    "CLAIM_STALE_SECONDS":
                        "60",
                },
                clear=False,
            ):
                first = acquire_claim(
                    db,
                    intent,
                )

                assert (
                    first.state
                    == "acquired"
                )

                second = acquire_claim(
                    db,
                    intent,
                )

                assert (
                    second.state
                    == "in_progress"
                )

    finally:
        engine.dispose()


def test_stale_claim_requires_reconciliation():
    engine = build_database()

    try:
        with Session(
            engine
        ) as db:
            run = (
                start_investigation_run(
                    db,
                    62,
                )
            )

            intent = make_intent(
                run_id=run.id
            )

            with patch.dict(
                os.environ,
                {
                    "SENTINEL_EXECUTION_"
                    "CLAIM_STALE_SECONDS":
                        "60",
                },
                clear=False,
            ):
                first = acquire_claim(
                    db,
                    intent,
                )

                assert (
                    first.state
                    == "acquired"
                )

                old_owner_token = (
                first.owner_token
                )

                claim = db.scalar(
                    select(
                        ExecutionClaim
                    ).where(
                        ExecutionClaim
                        .idempotency_key
                        ==
                        intent.idempotency_key
                    )
                )

                claim.updated_at = (
                    datetime.utcnow()
                    - timedelta(
                        seconds=120
                    )
                )

                db.commit()

                second = acquire_claim(
                    db,
                    intent,
                )

                assert (
                    second.state
                    ==
                    "reconciliation_required"
                )

                # Phase 3 is detection only.
                # Ownership must not change yet.
                refreshed = db.scalar(
                    select(
                        ExecutionClaim
                    ).where(
                        ExecutionClaim
                        .idempotency_key
                        ==
                        intent.idempotency_key
                    )
                )

                assert (
                    refreshed.owner_token
                    == second.owner_token
                )

                assert (
                    refreshed.owner_token
                    != old_owner_token
                )

                assert (
                    refreshed.attempt
                    == 1
                )

                assert (
                    refreshed.status
                    == "claimed"
                )

                assert (
                    refreshed.attempt
                    == 1
                )

                assert (
                    refreshed.status
                    == "claimed"
                )

    finally:
        engine.dispose()

def test_stale_owner_is_fenced():
    engine = build_database()

    try:
        with Session(
            engine
        ) as db:
            run = (
                start_investigation_run(
                    db,
                    62,
                )
            )

            intent = make_intent(
                run_id=run.id
            )

            with patch.dict(
                os.environ,
                {
                    "SENTINEL_EXECUTION_"
                    "CLAIM_STALE_SECONDS":
                        "60",
                },
                clear=False,
            ):
                first = acquire_claim(
                    db,
                    intent,
                )

                assert (
                    first.state
                    == "acquired"
                )

                old_owner_token = (
                    first.owner_token
                )

                claim = db.scalar(
                    select(
                        ExecutionClaim
                    ).where(
                        ExecutionClaim
                        .idempotency_key
                        ==
                        intent.idempotency_key
                    )
                )

                claim.updated_at = (
                    datetime.utcnow()
                    - timedelta(
                        seconds=120
                    )
                )

                db.commit()

                recovery = acquire_claim(
                    db,
                    intent,
                )

                assert (
                    recovery.state
                    ==
                    "reconciliation_required"
                )

                assert (
                    recovery.owner_token
                    != old_owner_token
                )

                from app.agent.execution_claims import (
                    finish_claim,
                )

                try:
                    finish_claim(
                        db,
                        intent,
                        old_owner_token,
                        status="completed",
                        receipt={},
                        output={},
                        event_id=0,
                    )

                except RuntimeError as exc:
                    db.rollback()

                    assert (
                        "ownership lost"
                        in str(exc).lower()
                    )

                else:
                    raise AssertionError(
                        "Stale owner unexpectedly "
                        "completed the claim."
                    )

                refreshed = db.scalar(
                    select(
                        ExecutionClaim
                    ).where(
                        ExecutionClaim
                        .idempotency_key
                        ==
                        intent.idempotency_key
                    )
                )

                assert (
                    refreshed.status
                    == "claimed"
                )

                assert (
                    refreshed.owner_token
                    ==
                    recovery.owner_token
                )

    finally:
        engine.dispose()

def test_recent_claim_below_threshold_not_stale():
    engine = build_database()

    try:
        with Session(
            engine
        ) as db:
            run = (
                start_investigation_run(
                    db,
                    62,
                )
            )

            intent = make_intent(
                run_id=run.id
            )

            with patch.dict(
                os.environ,
                {
                    "SENTINEL_EXECUTION_"
                    "CLAIM_STALE_SECONDS":
                        "60",
                },
                clear=False,
            ):
                acquire_claim(
                    db,
                    intent,
                )

                claim = db.scalar(
                    select(
                        ExecutionClaim
                    ).where(
                        ExecutionClaim
                        .idempotency_key
                        ==
                        intent.idempotency_key
                    )
                )

                claim.updated_at = (
                    datetime.utcnow()
                    - timedelta(
                        seconds=30
                    )
                )

                db.commit()

                result = acquire_claim(
                    db,
                    intent,
                )

                assert (
                    result.state
                    == "in_progress"
                )

    finally:
        engine.dispose()

def test_second_recovery_contender_is_blocked():
    engine = build_database()

    try:
        with Session(
            engine
        ) as db:
            run = (
                start_investigation_run(
                    db,
                    62,
                )
            )

            intent = make_intent(
                run_id=run.id
            )

            with patch.dict(
                os.environ,
                {
                    "SENTINEL_EXECUTION_"
                    "CLAIM_STALE_SECONDS":
                        "60",
                },
                clear=False,
            ):
                acquire_claim(
                    db,
                    intent,
                )

                claim = db.scalar(
                    select(
                        ExecutionClaim
                    ).where(
                        ExecutionClaim
                        .idempotency_key
                        ==
                        intent.idempotency_key
                    )
                )

                claim.updated_at = (
                    datetime.utcnow()
                    - timedelta(
                        seconds=120
                    )
                )

                db.commit()

                recovery = acquire_claim(
                    db,
                    intent,
                )

                assert (
                    recovery.state
                    ==
                    "reconciliation_required"
                )

                recovery_token = (
                    recovery.owner_token
                )

                second = acquire_claim(
                    db,
                    intent,
                )

                assert (
                    second.state
                    == "in_progress"
                )

                refreshed = db.scalar(
                    select(
                        ExecutionClaim
                    ).where(
                        ExecutionClaim
                        .idempotency_key
                        ==
                        intent.idempotency_key
                    )
                )

                assert (
                    refreshed.owner_token
                    == recovery_token
                )

    finally:
        engine.dispose()

def main():
    checks = (
        test_fresh_claim_remains_in_progress,
        test_stale_claim_requires_reconciliation,
        test_recent_claim_below_threshold_not_stale,
        test_stale_owner_is_fenced,
        test_second_recovery_contender_is_blocked,
    )

    for check in checks:
        check()

        print(
            f"[PASS] "
            f"{check.__name__}"
        )

    print(
        "\nClaim staleness "
        "evaluation PASSED"
    )


if __name__ == "__main__":
    main()