from app.agent.investigation_runner import (
    run_investigation_with_ledger,
)
from app.agent.ledger import (
    get_investigation_trace,
)
from app.agent.response_runner import (
    resolve_approval_with_ledger,
    run_response_pipeline,
)
from app.db.database import SessionLocal


TEST_FINDING_ID = 62


def main():
    db = SessionLocal()

    try:
        # ---------------------------------------------
        # Investigation
        # ---------------------------------------------

        state, run = (
            run_investigation_with_ledger(
                db,
                TEST_FINDING_ID,
            )
        )

        assert (
            state.get("status")
            == "grounding_completed"
        )

        print(
            "[PASS] grounded investigation completed"
        )

        # ---------------------------------------------
        # Response + Policy
        # ---------------------------------------------

        plan, evaluation, approvals = (
            run_response_pipeline(
                db,
                run_id=run.id,
                state=state,
            )
        )

        assert plan.dry_run is True

        print(
            "[PASS] dry-run response plan generated"
        )

        assert (
            len(evaluation.results)
            == len(plan.tool_requests)
        )

        print(
            "[PASS] policy evaluation completed"
        )

        # Finding 62 currently requires human review,
        # therefore there should be at least one
        # approval request.
        assert len(approvals) >= 1

        assert all(
            approval.status == "pending"
            for approval in approvals
        )

        print(
            "[PASS] human approval requested"
        )

        # ---------------------------------------------
        # Explicit test approval resolution
        #
        # This does NOT execute the tool.
        # ---------------------------------------------

        resolved = (
            resolve_approval_with_ledger(
                db,
                run_id=run.id,
                approval=approvals[0],
                approved=True,
                reviewer="test-security-analyst",
                reason=(
                    "Evaluator approved the request "
                    "for workflow validation only."
                ),
            )
        )

        assert resolved.status == "approved"

        print(
            "[PASS] approval resolved explicitly"
        )

        # ---------------------------------------------
        # Ledger validation
        # ---------------------------------------------

        trace = get_investigation_trace(
            db,
            run.id,
        )

        event_types = [
            event.event_type
            for event
            in trace.events
        ]

        assert (
            "response_planned"
            in event_types
        )

        assert (
            "policy_evaluated"
            in event_types
        )

        assert (
            "approval_requested"
            in event_types
        )

        assert (
            "approval_resolved"
            in event_types
        )

        print(
            "[PASS] response and policy audit "
            "trace persisted"
        )

        # ---------------------------------------------
        # Critical safety assertion:
        # approval is NOT execution.
        # ---------------------------------------------

        forbidden_execution_events = {
            "tool_executed",
            "block_ip_executed",
            "ticket_created",
            "notification_sent",
        }

        assert not any(
            event_type
            in forbidden_execution_events
            for event_type
            in event_types
        )

        print(
            "[PASS] approval did not execute tools"
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
            "\nResponse + Policy Runner "
            "evaluation PASSED"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()