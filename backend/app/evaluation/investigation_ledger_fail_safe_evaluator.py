from app.agent.investigation_runner import (
    run_investigation_with_ledger,
)
from app.agent.ledger import (
    get_investigation_trace,
)
from app.db.database import SessionLocal


INVALID_FINDING_ID = 999999


def main():
    db = SessionLocal()

    try:
        state, run = run_investigation_with_ledger(
            db,
            INVALID_FINDING_ID,
        )

        # ---------------------------------------------
        # 1. Graph must fail safely
        # ---------------------------------------------

        assert state.get("status") == "failed"
        assert state.get("failed_node") == "build_context"
        assert state.get("error") is not None

        print(
            "[PASS] invalid finding failed safely"
        )

        # ---------------------------------------------
        # 2. InvestigationRun must be persisted as failed
        # ---------------------------------------------

        assert run.finding_id == INVALID_FINDING_ID
        assert run.status == "failed"
        assert run.final_verdict is None
        assert run.error_message is not None
        assert run.finished_at is not None

        print(
            "[PASS] failed investigation persisted"
        )

        # ---------------------------------------------
        # 3. Failure event must exist
        # ---------------------------------------------

        trace = get_investigation_trace(
            db,
            run.id,
        )

        assert trace.run.status == "failed"
        assert len(trace.events) >= 1

        failure_events = [
            event
            for event in trace.events
            if event.event_type
            == "investigation_failed"
        ]

        assert len(failure_events) == 1

        failure_event = failure_events[0]

        assert failure_event.status == "failed"
        assert (
            failure_event.node_name
            == "build_context"
        )

        print(
            "[PASS] failure audit event recorded"
        )

        # ---------------------------------------------
        # 4. Error information must remain auditable
        # ---------------------------------------------

        assert "Finding not found" in (
            run.error_message
        )

        assert "Finding not found" in (
            failure_event.summary or ""
        )

        print(
            "[PASS] failure reason preserved"
        )

        print(
            f"\nFailed Investigation Run: "
            f"{run.id}"
        )

        print(
            f"Failed Node: "
            f"{state.get('failed_node')}"
        )

        print(
            f"Error: "
            f"{state.get('error')}"
        )

        print(
            "\nInvestigation Ledger "
            "Fail-Safe evaluation PASSED"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()