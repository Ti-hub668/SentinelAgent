from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dataclasses import replace
from datetime import timezone
from unittest.mock import patch

from app.agent.execution_claims import (
    acquire_claim,
)
from app.agent.reconciliation_service import (
    reconcile_run,
)
from app.agent.tool_registry import (
    TOOL_REGISTRY,
)
from app.schemas.execution import (
    ExecutionAuthorizationSnapshot,
    ExecutionIntent,
)
from app.schemas.reconciliation import (
    ToolReconciliationResult,
)
from app.agent.execution_claims import (
    acquire_reconciliation_claim,
)
from app.db.database import Base
from app.models.execution_claim import (
    ExecutionClaim,
)
from app.models.investigation_run import (
    InvestigationRun,
)

class TestReconciliationAdapter:
    def __init__(
        self,
        result: ToolReconciliationResult,
    ):
        self.result = result
        self.execute_calls = 0
        self.reconcile_calls = 0

    def execute(
        self,
        *,
        parameters,
        dry_run=True,
        execution_context=None,
    ):
        self.execute_calls += 1

        raise AssertionError(
            "Reconciliation must never invoke "
            "adapter.execute()."
        )

    def reconcile(
        self,
        *,
        execution_context,
    ):
        self.reconcile_calls += 1

        return self.result

def test_confirmed_reconciliation_completes_claim():
    engine = build_engine()

    run_id, claim_id = seed_claim(
        engine,
        updated_at=datetime(
            2000,
            1,
            1,
        ),
    )

    adapter = TestReconciliationAdapter(
        ToolReconciliationResult(
            state="confirmed_completed",
            message=(
                "Existing external ticket "
                "confirmed."
            ),
            output={
                "provider": "github_issues",
                "ticket_number": 321,
                "ticket_url": (
                    "https://example.test/"
                    "issues/321"
                ),
                "reconciled": True,
            },
        )
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=adapter,
            )
        },
    ):
        with Session(engine) as db:
            summary = reconcile_run(
                db,
                run_id=run_id,
            )

    assert summary.checked == 1
    assert summary.confirmed == 1
    assert summary.unresolved == 0
    assert summary.failed == 0

    assert adapter.reconcile_calls == 1
    assert adapter.execute_calls == 0

    with Session(engine) as db:
        claim = db.get(
            ExecutionClaim,
            claim_id,
        )

        assert claim is not None
        assert claim.status == "completed"

        assert (
            claim.output[
                "ticket_number"
            ]
            == 321
        )

        assert (
            claim.receipt[
                "outcome"
            ]
            == "executed"
        )

        assert (
            claim.receipt[
                "executor_invoked"
            ]
            is True
        )

def test_not_found_remains_claimed():
    engine = build_engine()

    run_id, claim_id = seed_claim(
        engine,
        updated_at=datetime(
            2000,
            1,
            1,
        ),
    )

    adapter = TestReconciliationAdapter(
        ToolReconciliationResult(
            state="not_found",
            message=(
                "No external ticket could "
                "be confirmed."
            ),
            output={
                "provider": "github_issues",
            },
        )
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=adapter,
            )
        },
    ):
        with Session(engine) as db:
            summary = reconcile_run(
                db,
                run_id=run_id,
            )

    assert summary.checked == 1
    assert summary.confirmed == 0
    assert summary.unresolved == 1
    assert summary.failed == 0

    assert adapter.reconcile_calls == 1
    assert adapter.execute_calls == 0

    with Session(engine) as db:
        claim = db.get(
            ExecutionClaim,
            claim_id,
        )

        assert claim is not None

        # Uncertain external state must remain
        # protected from automatic retry.
        assert claim.status == "claimed"

def test_recovered_claim_becomes_replayable():
    engine = build_engine()

    run_id, claim_id = seed_claim(
        engine,
        updated_at=datetime(
            2000,
            1,
            1,
        ),
    )

    adapter = TestReconciliationAdapter(
        ToolReconciliationResult(
            state="confirmed_completed",
            message=(
                "Existing ticket confirmed."
            ),
            output={
                "ticket_number": 456,
                "reconciled": True,
            },
        )
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=adapter,
            )
        },
    ):
        with Session(engine) as db:
            reconcile_run(
                db,
                run_id=run_id,
            )

    with Session(engine) as db:
        claim = db.get(
            ExecutionClaim,
            claim_id,
        )

        intent = ExecutionIntent(
            execution_id=(
                claim.execution_id
            ),
            finding_id=1,
            run_id=run_id,
            request_index=(
                claim.request_index
            ),
            tool_name="create_ticket",
            target="finding:1",
            request_fingerprint=(
                claim.request_fingerprint
            ),
            idempotency_key=(
                claim.idempotency_key
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
            created_at=datetime.now(
                timezone.utc
            ),
        )

        replay = acquire_claim(
            db,
            intent,
        )

    assert replay.state == "completed"

    assert (
        replay.output[
            "ticket_number"
        ]
        == 456
    )

    assert adapter.execute_calls == 0

def test_reconciliation_writes_audit_event():
    engine = build_engine()

    run_id, _ = seed_claim(
        engine,
        updated_at=datetime(
            2000,
            1,
            1,
        ),
    )

    adapter = TestReconciliationAdapter(
        ToolReconciliationResult(
            state="confirmed_completed",
            message="Confirmed.",
            output={
                "ticket_number": 789,
            },
        )
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=adapter,
            )
        },
    ):
        with Session(engine) as db:
            reconcile_run(
                db,
                run_id=run_id,
            )

    from app.models.investigation_event import (
        InvestigationEvent,
    )

    with Session(engine) as db:
        events = (
            db.query(
                InvestigationEvent
            )
            .filter(
                InvestigationEvent.run_id
                == run_id
            )
            .order_by(
                InvestigationEvent.id.asc()
            )
            .all()
        )

    event_types = [
        event.event_type
        for event in events
    ]

    assert (
        "tool_reconciliation_started"
        in event_types
    )

    assert (
        "tool_reconciliation_confirmed"
        in event_types
    )

def build_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    return engine


def seed_claim(
    engine,
    *,
    updated_at: datetime,
):
    with Session(engine) as db:
        run = InvestigationRun(
            finding_id=1,
            status="running",
        )

        db.add(run)
        db.commit()
        db.refresh(run)

        claim = ExecutionClaim(
            run_id=run.id,
            request_index=0,
            idempotency_key=(
                "reconcile-slot-001"
            ),
            request_fingerprint=(
                "reconcile-fingerprint-001"
            ),
            execution_id=(
                "reconcile-execution-001"
            ),
            tool_name="create_ticket",
            status="claimed",
            attempt=1,
            owner_token="original-owner",
            updated_at=updated_at,
        )

        db.add(claim)
        db.commit()
        db.refresh(claim)

        return run.id, claim.id


def test_fresh_claim_not_acquired():
    engine = build_engine()

    _, claim_id = seed_claim(
        engine,
        updated_at=datetime.utcnow(),
    )

    with Session(engine) as db:
        result = (
            acquire_reconciliation_claim(
                db,
                claim_id=claim_id,
            )
        )

    assert (
        result.state
        == "not_stale"
    )


def test_stale_claim_acquired_once():
    engine = build_engine()

    _, claim_id = seed_claim(
        engine,
        updated_at=datetime(
            2000,
            1,
            1,
        ),
    )

    with Session(engine) as db:
        first = (
            acquire_reconciliation_claim(
                db,
                claim_id=claim_id,
            )
        )

    assert first.state == "acquired"

    assert (
        first.owner_token
        is not None
    )

    with Session(engine) as db:
        second = (
            acquire_reconciliation_claim(
                db,
                claim_id=claim_id,
            )
        )

    assert (
        second.state
        == "not_stale"
    )


def main():
    checks = (
        test_fresh_claim_not_acquired,
        test_stale_claim_acquired_once,
        test_confirmed_reconciliation_completes_claim,
        test_not_found_remains_claimed,
        test_recovered_claim_becomes_replayable,
        test_reconciliation_writes_audit_event,
    )

    for check in checks:
        check()

        print(
            f"[PASS] {check.__name__}"
        )

    print(
        "\nReconciliation service "
        "ownership evaluation PASSED"
    )


if __name__ == "__main__":
    main()