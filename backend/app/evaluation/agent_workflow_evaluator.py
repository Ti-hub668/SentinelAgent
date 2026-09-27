from app.agent.orchestrator import (
    execute_workflow_tools,
    get_workflow_summary,
    resolve_workflow_approval,
    start_agent_workflow,
)
from app.agent.ledger import (
    get_investigation_trace,
)
from app.db.database import SessionLocal


TEST_FINDING_ID = 62


def main():
    db = SessionLocal()

    try:
        # --------------------------------------------------
        # 1. Start complete workflow
        # --------------------------------------------------

        summary = start_agent_workflow(
            db,
            TEST_FINDING_ID,
        )

        assert summary.run_id > 0

        assert (
            summary.response_plan
            is not None
        )

        assert (
            summary.policy_evaluation
            is not None
        )

        print(
            "[PASS] full workflow started"
        )

        print(
            "Workflow status:",
            summary.workflow_status,
        )

        # --------------------------------------------------
        # 2. Restore workflow from Ledger
        # --------------------------------------------------

        restored = get_workflow_summary(
            db,
            summary.run_id,
        )

        assert (
            restored.run_id
            == summary.run_id
        )

        assert (
            restored.response_plan
            is not None
        )

        assert (
            restored.policy_evaluation
            is not None
        )

        print(
            "[PASS] workflow restored from Ledger"
        )

        # --------------------------------------------------
        # 3. Resolve pending approval
        # --------------------------------------------------

        if restored.approvals:
            approval = (
                restored.approvals[0]
            )

            assert (
                approval.status
                == "pending"
            )

            restored = (
                resolve_workflow_approval(
                    db,
                    run_id=summary.run_id,
                    request_index=(
                        approval.request_index
                    ),
                    approved=True,
                    reviewer=(
                        "test-security-analyst"
                    ),
                    reason=(
                        "Day28 unified workflow "
                        "integration test."
                    ),
                )
            )

            resolved = next(
                item
                for item
                in restored.approvals
                if (
                    item.request_index
                    == approval.request_index
                )
            )

            assert (
                resolved.status
                == "approved"
            )

            print(
                "[PASS] approval restored "
                "and resolved"
            )

        # --------------------------------------------------
        # 4. Send authorized requests to Tool Broker
        # --------------------------------------------------

        batch = execute_workflow_tools(
            db,
            run_id=summary.run_id,
        )

        assert all(
            result.dry_run is True
            for result
            in batch.results
        )

        print(
            "[PASS] authorized requests "
            "processed by Tool Broker"
        )

        # --------------------------------------------------
        # 5. Restore Tool Broker results
        # --------------------------------------------------

        final_summary = (
            get_workflow_summary(
                db,
                summary.run_id,
            )
        )

        assert (
            len(final_summary.tool_results)
            >= 1
        )

        print(
            "[PASS] Tool Broker results "
            "restored from Ledger"
        )

        # --------------------------------------------------
        # 6. Inspect full audit trace
        # --------------------------------------------------

        trace = get_investigation_trace(
            db,
            summary.run_id,
        )

        print(
            f"\nRun ID: {summary.run_id}"
        )

        print(
            "Final workflow status:",
            final_summary.workflow_status,
        )

        print(
            "Events:",
            len(trace.events),
        )

        for event in trace.events:
            print(
                f"  {event.id}: "
                f"{event.event_type} "
                f"[{event.status}]"
            )

        print(
            "\nFull Agent Workflow "
            "evaluation PASSED"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()