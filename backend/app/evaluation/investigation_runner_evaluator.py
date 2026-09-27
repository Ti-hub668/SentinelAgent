from app.agent.investigation_runner import (
    run_investigation_with_ledger,
)
from app.agent.ledger import (
    get_investigation_trace,
)
from app.db.database import SessionLocal


TEST_FINDING_ID = 62


def main():
    db = SessionLocal()

    try:
        state, run = (
            run_investigation_with_ledger(
                db,
                TEST_FINDING_ID,
            )
        )

        assert run.finding_id == TEST_FINDING_ID

        assert (
            state.get("status")
            == "grounding_completed"
        )

        assert run.status == "completed"

        assert run.final_verdict is not None

        print(
            "[PASS] real investigation completed"
        )

        trace = get_investigation_trace(
            db,
            run.id,
        )

        assert trace.run.id == run.id

        assert len(trace.events) >= 5

        event_types = [
            event.event_type
            for event in trace.events
        ]

        assert "context_built" in event_types
        assert "triage_completed" in event_types
        assert "evidence_assessed" in event_types
        assert "risk_enriched" in event_types
        assert "grounding_validated" in event_types

        print(
            "[PASS] real audit trace persisted"
        )

        grounding = state[
            "grounding_result"
        ]

        assert (
            trace.run.final_verdict
            == grounding.grounded_verdict
        )

        print(
            "[PASS] grounded verdict persisted"
        )

        print(
            f"\nInvestigation Run: {run.id}"
        )

        for event in trace.events:
            print(
                f"  {event.id}: "
                f"{event.event_type} "
                f"[{event.status}]"
            )

        print(
            "\nInvestigation Runner "
            "evaluation PASSED"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()