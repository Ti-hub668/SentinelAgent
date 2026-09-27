from app.agent.ledger import (
    complete_investigation_run,
    get_investigation_trace,
    record_investigation_event,
    start_investigation_run,
)
from app.db.database import SessionLocal


TEST_FINDING_ID = 62


def main():
    db = SessionLocal()

    try:
        # --------------------------------------------------
        # 1. Start investigation
        # --------------------------------------------------

        run = start_investigation_run(
            db,
            TEST_FINDING_ID,
        )

        assert run.finding_id == TEST_FINDING_ID
        assert run.status == "running"

        print(
            f"[PASS] investigation run started: "
            f"run_id={run.id}"
        )

        # --------------------------------------------------
        # 2. Record context event
        # --------------------------------------------------

        context_event = record_investigation_event(
            db,
            run_id=run.id,
            event_type="context_built",
            node_name="build_context",
            summary=(
                "Investigation context built "
                "for Finding 62."
            ),
            event_metadata={
                "finding_id": TEST_FINDING_ID,
            },
        )

        assert context_event.run_id == run.id
        assert context_event.status == "completed"

        print(
            "[PASS] context event recorded"
        )

        # --------------------------------------------------
        # 3. Record triage event
        # --------------------------------------------------

        triage_event = record_investigation_event(
            db,
            run_id=run.id,
            event_type="triage_completed",
            node_name="triage",
            summary=(
                "Finding routed through "
                "investigation triage."
            ),
            event_metadata={
                "needs_research": True,
            },
        )

        assert triage_event.run_id == run.id

        print(
            "[PASS] triage event recorded"
        )

        # --------------------------------------------------
        # 4. Record grounding event
        # --------------------------------------------------

        grounding_event = record_investigation_event(
            db,
            run_id=run.id,
            event_type="grounding_validated",
            node_name="grounding",
            summary=(
                "Final verdict passed "
                "grounding validation."
            ),
            event_metadata={
                "grounding_status": "supported",
                "grounding_score": 1.0,
                "requires_human_review": False,
            },
        )

        assert grounding_event.run_id == run.id

        print(
            "[PASS] grounding event recorded"
        )

        # --------------------------------------------------
        # 5. Complete investigation
        # --------------------------------------------------

        completed_run = complete_investigation_run(
            db,
            run_id=run.id,
            final_verdict="likely_true_positive",
        )

        assert completed_run.status == "completed"
        assert (
            completed_run.final_verdict
            == "likely_true_positive"
        )
        assert completed_run.finished_at is not None

        print(
            "[PASS] investigation run completed"
        )

        # --------------------------------------------------
        # 6. Read complete audit trace
        # --------------------------------------------------

        trace = get_investigation_trace(
            db,
            run.id,
        )

        assert trace.run.id == run.id
        assert trace.run.status == "completed"
        assert len(trace.events) == 3

        event_types = [
            event.event_type
            for event in trace.events
        ]

        assert event_types == [
            "context_built",
            "triage_completed",
            "grounding_validated",
        ]

        print(
            "[PASS] investigation trace loaded"
        )

        print("\nAudit Trace")

        for event in trace.events:
            print(
                f"  {event.id}: "
                f"{event.event_type} "
                f"[{event.status}]"
            )

        print(
            "\nInvestigation Ledger "
            "evaluation PASSED"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()