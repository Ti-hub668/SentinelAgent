from app.agent.investigation_runner import (
    run_investigation_with_ledger,
)
from app.agent.response_agent import (
    generate_response_plan,
)
from app.db.database import SessionLocal


TEST_FINDING_ID = 62


def main():
    db = SessionLocal()

    try:
        state, _ = (
            run_investigation_with_ledger(
                db,
                TEST_FINDING_ID,
            )
        )

        assert (
            state.get("status")
            == "grounding_completed"
        )

        plan = generate_response_plan(
            state
        )

        assert (
            plan.finding_id
            == TEST_FINDING_ID
        )

        assert plan.dry_run is True

        assert plan.grounded_verdict

        assert plan.decision_action

        assert plan.summary.strip()

        assert isinstance(
            plan.containment_plan,
            list,
        )

        assert isinstance(
            plan.remediation_plan,
            list,
        )

        assert isinstance(
            plan.verification_plan,
            list,
        )

        assert isinstance(
            plan.tool_requests,
            list,
        )

        print(
            "[PASS] response plan generated"
        )

        print(
            "[PASS] response remains dry-run"
        )

        grounding = state[
            "grounding_result"
        ]

        if grounding.requires_human_review:
            assert all(
                request.tool_name
                != "block_ip"
                for request
                in plan.tool_requests
            )

            print(
                "[PASS] unsafe containment "
                "suppressed during review"
            )

        print(
            "\nResponse Plan"
        )

        print(
            "Decision:",
            plan.decision_action,
        )

        print(
            "Priority:",
            plan.priority,
        )

        print(
            "Human Review:",
            plan.requires_human_review,
        )

        print(
            "Tool Requests:",
            [
                request.tool_name
                for request
                in plan.tool_requests
            ],
        )

        print(
            "\nResponse Agent "
            "evaluation PASSED"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()