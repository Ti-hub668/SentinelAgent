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
from app.agent.tool_broker import (
    execute_policy_evaluation_with_ledger,
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
            "[PASS] investigation completed"
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

        assert len(approvals) >= 1

        print(
            "[PASS] approval-gated "
            "response generated"
        )

        # ---------------------------------------------
        # Before approval:
        # Broker MUST block.
        # ---------------------------------------------

        blocked_batch = (
            execute_policy_evaluation_with_ledger(
                db,
                run_id=run.id,
                evaluation=evaluation,
                approvals=approvals,
            )
        )

        assert (
            blocked_batch.simulated_count
            == 0
        )

        assert (
            blocked_batch.blocked_count
            >= 1
        )

        print(
            "[PASS] pending request blocked "
            "by Tool Broker"
        )

        # ---------------------------------------------
        # Approve first request.
        # ---------------------------------------------

        approved = (
            resolve_approval_with_ledger(
                db,
                run_id=run.id,
                approval=approvals[0],
                approved=True,
                reviewer=(
                    "test-security-analyst"
                ),
                reason=(
                    "Approved for dry-run "
                    "broker validation."
                ),
            )
        )

        assert approved.status == "approved"

        print(
            "[PASS] human approval resolved"
        )

        # ---------------------------------------------
        # After approval:
        # Mock executor may run.
        # ---------------------------------------------

        approved_batch = (
            execute_policy_evaluation_with_ledger(
                db,
                run_id=run.id,
                evaluation=evaluation,
                approvals=[approved],
            )
        )

        assert (
            approved_batch.simulated_count
            >= 1
        )

        assert all(
            result.dry_run is True
            for result
            in approved_batch.results
        )

        print(
            "[PASS] approved request reached "
            "dry-run executor"
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
            "tool_execution_blocked"
            in event_types
        )

        assert (
            "tool_execution_simulated"
            in event_types
        )

        print(
            "[PASS] Tool Broker audit "
            "events persisted"
        )

        # No real execution event exists.
        forbidden_events = {
            "firewall_modified",
            "ip_blocked_real",
            "ticket_created_real",
            "notification_sent_real",
        }

        assert not any(
            event_type
            in forbidden_events
            for event_type
            in event_types
        )

        print(
            "[PASS] no real side effects "
            "were recorded"
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
            "\nTool Broker Integration "
            "evaluation PASSED"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()