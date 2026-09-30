"""Offline Day42 execution idempotency and replay checks."""

from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent.approval import approve_request
from app.agent.execution_guard import (
    build_idempotency_key,
    build_request_fingerprint,
)
from app.agent.ledger import (
    get_investigation_trace,
    start_investigation_run,
)
from app.agent.policy_engine import (
    build_approval_requests,
    evaluate_response_plan,
)
from app.agent.tool_broker import (
    execute_policy_evaluation_with_ledger,
)
from app.agent.tool_registry import TOOL_REGISTRY
from app.evaluation.tool_broker_evaluator import make_plan
from app.models.investigation_event import InvestigationEvent
from app.models.investigation_run import InvestigationRun
from app.schemas.response_plan import ToolRequest


@contextmanager
def isolated_ledger():
    """
    Create an isolated in-memory Ledger.

    No application DB writes.
    """

    engine = create_engine(
        "sqlite:///:memory:"
    )

    InvestigationRun.__table__.create(
        engine
    )

    InvestigationEvent.__table__.create(
        engine
    )

    try:
        with Session(engine) as db:
            yield db

    finally:
        engine.dispose()


def make_request(
    *,
    tool_name="create_ticket",
    target="finding:62",
    reason="Day42 execution test.",
    parameters=None,
):
    return ToolRequest(
        tool_name=tool_name,
        target=target,
        reason=reason,
        parameters=(
            parameters
            if parameters is not None
            else {}
        ),
    )


def make_evaluation(
    request: ToolRequest,
    *,
    requires_human_review=False,
):
    return evaluate_response_plan(
        make_plan(
            request=request,
            requires_human_review=(
                requires_human_review
            ),
        )
    )


def execute_with_ledger(
    db: Session,
    *,
    run_id: int,
    request: ToolRequest,
    approvals=None,
):
    evaluation = make_evaluation(
        request
    )

    return (
        execute_policy_evaluation_with_ledger(
            db,
            run_id=run_id,
            evaluation=evaluation,
            approvals=(
                approvals
                if approvals is not None
                else []
            ),
        )
    )


def test_canonical_request_fingerprint():
    first = make_request(
        tool_name="manual_review",
        reason="First wording.",
        parameters={
            "finding_id": 62,
            "grounded_verdict":
                "likely_true_positive",
        },
    )

    second = make_request(
        tool_name="manual_review",
        reason="Completely different wording.",
        parameters={
            "grounded_verdict":
                "likely_true_positive",
            "finding_id": 62,
        },
    )

    first_fingerprint = (
        build_request_fingerprint(
            first
        )
    )

    second_fingerprint = (
        build_request_fingerprint(
            second
        )
    )

    # reason is intentionally excluded and
    # dict ordering must not matter.
    assert (
        first_fingerprint
        == second_fingerprint
    )

    changed = make_request(
        tool_name="manual_review",
        parameters={
            "finding_id": 62,
            "grounded_verdict":
                "false_positive",
        },
    )

    assert (
        build_request_fingerprint(
            changed
        )
        != first_fingerprint
    )

    # Idempotency key identifies the execution slot,
    # not request semantics.
    first_key = build_idempotency_key(
        run_id=42,
        request_index=0,
    )

    second_key = build_idempotency_key(
        run_id=42,
        request_index=0,
    )

    assert first_key == second_key
    assert first_key != build_idempotency_key(run_id=42, request_index=1)

    different_run_key = (
        build_idempotency_key(
            run_id=43,
            request_index=0,
        )
    )

    assert (
        different_run_key
        != first_key
    )


def test_same_run_replay_deduplicated():
    with isolated_ledger() as db:
        run = start_investigation_run(
            db,
            62,
        )

        request = make_request()

        definition = (
            TOOL_REGISTRY[
                "create_ticket"
            ]
        )

        executor = Mock(
            return_value={
                "ticket_id":
                    "dry-run-ticket",
            }
        )

        with patch.dict(
            TOOL_REGISTRY,
            {
                "create_ticket":
                    replace(
                        definition,
                        executor=executor,
                    )
            },
        ):
            first = execute_with_ledger(
                db,
                run_id=run.id,
                request=request,
            )

            second = execute_with_ledger(
                db,
                run_id=run.id,
                request=request,
            )

        first_result = (
            first.results[0]
        )

        second_result = (
            second.results[0]
        )

        assert (
            first_result.status
            == "simulated"
        )
        assert first_result.executed
        assert not first_result.replayed

        assert (
            second_result.status
            == "simulated"
        )
        assert not second_result.executed
        assert second_result.replayed

        executor.assert_called_once()

        assert (
            first_result
            .execution_intent
            .idempotency_key
            ==
            second_result
            .execution_intent
            .idempotency_key
        )

        assert (
            first_result
            .execution_intent
            .request_fingerprint
            ==
            second_result
            .execution_intent
            .request_fingerprint
        )

        assert (
            first_result
            .execution_intent
            .execution_id
            ==
            second_result
            .execution_intent
            .execution_id
        )

        assert (
            second_result
            .execution_receipt
            .replayed
        )

        assert (
            second_result
            .execution_receipt
            .executor_invoked
            is False
        )

        trace = get_investigation_trace(
            db,
            run.id,
        )

        assert [
            event.event_type
            for event
            in trace.events
        ] == [
            "tool_execution_simulated",
            "tool_execution_replayed",
        ]


def test_replay_fingerprint_mismatch_blocked():
    with isolated_ledger() as db:
        run = start_investigation_run(
            db,
            62,
        )

        definition = (
            TOOL_REGISTRY[
                "create_ticket"
            ]
        )

        executor = Mock(
            return_value={
                "ticket_id":
                    "dry-run-ticket",
            }
        )

        first_request = make_request(
            target="finding:62",
        )

        # Same run + same request_index,
        # but changed execution semantics.
        changed_request = make_request(
            target="finding:63",
        )

        with patch.dict(
            TOOL_REGISTRY,
            {
                "create_ticket":
                    replace(
                        definition,
                        executor=executor,
                    )
            },
        ):
            first = execute_with_ledger(
                db,
                run_id=run.id,
                request=first_request,
            )

            second = execute_with_ledger(
                db,
                run_id=run.id,
                request=changed_request,
            )

        assert (
            first.results[0].status
            == "simulated"
        )

        mismatch = second.results[0]

        assert (
            mismatch.status
            == "blocked"
        )
        assert mismatch.executed is False
        assert mismatch.replayed is False

        assert (
            "fingerprint"
            in mismatch.message.lower()
        )

        # Changed request must NOT reach executor.
        executor.assert_called_once()

        assert (
            first.results[0]
            .execution_intent
            .idempotency_key
            ==
            mismatch
            .execution_intent
            .idempotency_key
        )

        assert (
            first.results[0]
            .execution_intent
            .request_fingerprint
            !=
            mismatch
            .execution_intent
            .request_fingerprint
        )

        trace = get_investigation_trace(
            db,
            run.id,
        )

        assert [
            event.event_type
            for event
            in trace.events
        ] == [
            "tool_execution_simulated",
            "tool_execution_blocked",
        ]


def test_different_runs_remain_independent():
    with isolated_ledger() as db:
        first_run = (
            start_investigation_run(
                db,
                62,
            )
        )

        second_run = (
            start_investigation_run(
                db,
                62,
            )
        )

        request = make_request()

        definition = (
            TOOL_REGISTRY[
                "create_ticket"
            ]
        )

        executor = Mock(
            return_value={
                "ticket_id":
                    "dry-run-ticket",
            }
        )

        with patch.dict(
            TOOL_REGISTRY,
            {
                "create_ticket":
                    replace(
                        definition,
                        executor=executor,
                    )
            },
        ):
            first = execute_with_ledger(
                db,
                run_id=first_run.id,
                request=request,
            )

            second = execute_with_ledger(
                db,
                run_id=second_run.id,
                request=request,
            )

        assert (
            first.results[0].executed
            is True
        )

        assert (
            second.results[0].executed
            is True
        )

        assert not first.results[0].replayed
        assert not second.results[0].replayed

        assert executor.call_count == 2

        assert (
            first.results[0]
            .execution_intent
            .idempotency_key
            !=
            second.results[0]
            .execution_intent
            .idempotency_key
        )


def test_approval_before_execution_and_replay():
    with isolated_ledger() as db:
        run = start_investigation_run(
            db,
            62,
        )

        request = make_request(
            tool_name="block_ip",
            target="192.0.2.10",
            reason="Contain suspicious host.",
        )

        evaluation = make_evaluation(
            request
        )

        assert (
            evaluation.results[0].decision
            == "REQUIRE_APPROVAL"
        )

        approvals = (
            build_approval_requests(
                evaluation
            )
        )

        definition = (
            TOOL_REGISTRY[
                "block_ip"
            ]
        )

        executor = Mock(
            return_value={
                "blocked":
                    "192.0.2.10",
            }
        )

        with patch.dict(
            TOOL_REGISTRY,
            {
                "block_ip":
                    replace(
                        definition,
                        executor=executor,
                    )
            },
        ):
            pending = (
                execute_policy_evaluation_with_ledger(
                    db,
                    run_id=run.id,
                    evaluation=evaluation,
                    approvals=approvals,
                )
            )

            assert (
                pending.results[0].status
                == "blocked"
            )

            assert (
                pending.results[0]
                .execution_intent
                is None
            )

            executor.assert_not_called()

            approved = approve_request(
                approvals[0],
                reviewer=(
                    "security-analyst"
                ),
                reason=(
                    "Containment approved."
                ),
            )

            first = (
                execute_policy_evaluation_with_ledger(
                    db,
                    run_id=run.id,
                    evaluation=evaluation,
                    approvals=[
                        approved
                    ],
                )
            )

            second = (
                execute_policy_evaluation_with_ledger(
                    db,
                    run_id=run.id,
                    evaluation=evaluation,
                    approvals=[
                        approved
                    ],
                )
            )

        assert first.results[0].executed
        assert not first.results[0].replayed

        assert (
            second.results[0].executed
            is False
        )
        assert second.results[0].replayed

        executor.assert_called_once()


def test_invalid_parameters_blocked_before_intent():
    with isolated_ledger() as db:
        run = start_investigation_run(
            db,
            62,
        )

        request = make_request(
            parameters={
                "dangerous_option":
                    True,
            }
        )

        definition = (
            TOOL_REGISTRY[
                "create_ticket"
            ]
        )

        executor = Mock()

        with patch.dict(
            TOOL_REGISTRY,
            {
                "create_ticket":
                    replace(
                        definition,
                        executor=executor,
                    )
            },
        ):
            result = execute_with_ledger(
                db,
                run_id=run.id,
                request=request,
            )

        broker_result = (
            result.results[0]
        )

        assert (
            broker_result.status
            == "blocked"
        )

        assert not broker_result.executed

        assert (
            broker_result
            .execution_intent
            is None
        )

        assert (
            broker_result
            .execution_receipt
            is None
        )

        executor.assert_not_called()


def test_failed_execution_remains_retryable():
    with isolated_ledger() as db:
        run = start_investigation_run(
            db,
            62,
        )

        request = make_request()

        definition = (
            TOOL_REGISTRY[
                "create_ticket"
            ]
        )

        executor = Mock(
            side_effect=[
                RuntimeError(
                    "temporary failure"
                ),
                {
                    "ticket_id":
                        "retry-success",
                },
            ]
        )

        with patch.dict(
            TOOL_REGISTRY,
            {
                "create_ticket":
                    replace(
                        definition,
                        executor=executor,
                    )
            },
        ):
            first = execute_with_ledger(
                db,
                run_id=run.id,
                request=request,
            )

            second = execute_with_ledger(
                db,
                run_id=run.id,
                request=request,
            )

        first_result = (
            first.results[0]
        )

        second_result = (
            second.results[0]
        )

        assert (
            first_result.status
            == "failed"
        )

        assert (
            second_result.status
            == "simulated"
        )

        assert second_result.executed
        assert not second_result.replayed

        assert executor.call_count == 2

        assert (
            first_result
            .execution_intent
            .idempotency_key
            ==
            second_result
            .execution_intent
            .idempotency_key
        )

        assert (
            first_result
            .execution_intent
            .attempt
            == 1
        )

        assert (
            second_result
            .execution_intent
            .attempt
            == 2
        )

        assert (
            first_result
            .execution_receipt
            .outcome
            == "failed"
        )

        assert (
            second_result
            .execution_receipt
            .outcome
            == "simulated"
        )

        trace = get_investigation_trace(
            db,
            run.id,
        )

        assert [
            event.event_type
            for event
            in trace.events
        ] == [
            "tool_execution_failed",
            "tool_execution_simulated",
        ]


def test_current_authorization_precedes_replay():
    with isolated_ledger() as db:
        run = start_investigation_run(db, 62)
        evaluation = make_evaluation(make_request(tool_name="block_ip", target="192.0.2.10"))
        pending = build_approval_requests(evaluation)[0]
        approved = approve_request(pending, reviewer="analyst", reason="test")
        executor = Mock(return_value={"ok": True})
        with patch.dict(TOOL_REGISTRY, {"block_ip": replace(TOOL_REGISTRY["block_ip"], executor=executor)}):
            first = execute_policy_evaluation_with_ledger(db, run_id=run.id,
                evaluation=evaluation, approvals=[approved])
            assert first.results[0].executed
            rejected = approved.model_copy(update={"status": "rejected"})
            for approvals in ([], [pending], [rejected], [approved, rejected]):
                result = execute_policy_evaluation_with_ledger(db, run_id=run.id,
                    evaluation=evaluation, approvals=approvals).results[0]
                assert result.status == "blocked" and not result.replayed
                assert result.execution_intent is None
            denied = evaluation.model_copy(deep=True)
            denied.results[0].decision = "DENY"
            result = execute_policy_evaluation_with_ledger(db, run_id=run.id,
                evaluation=denied, approvals=[approved]).results[0]
            assert result.status == "blocked" and not result.replayed
            executor.assert_called_once()


def test_approval_is_bound_to_finding_and_parameters():
    with isolated_ledger() as db:
        run = start_investigation_run(db, 62)
        request = make_request(tool_name="manual_review", parameters={
            "finding_id": 62, "grounded_verdict": "likely_true_positive"})
        evaluation = make_evaluation(request)
        approved = approve_request(build_approval_requests(evaluation)[0],
            reviewer="analyst", reason="test")
        changed = evaluation.model_copy(deep=True)
        changed.results[0].tool_request.parameters["grounded_verdict"] = "false_positive"
        executor = Mock(return_value={"ok": True})
        with patch.dict(TOOL_REGISTRY, {"manual_review": replace(TOOL_REGISTRY["manual_review"], executor=executor)}):
            result = execute_policy_evaluation_with_ledger(db, run_id=run.id,
                evaluation=changed, approvals=[approved]).results[0]
            assert result.status == "blocked" and result.execution_intent is None
            wrong_finding = approved.model_copy(update={"finding_id": 63})
            result = execute_policy_evaluation_with_ledger(db, run_id=run.id,
                evaluation=evaluation, approvals=[wrong_finding]).results[0]
            assert result.status == "blocked" and result.execution_intent is None
            executor.assert_not_called()
            result = execute_policy_evaluation_with_ledger(db, run_id=run.id,
                evaluation=evaluation, approvals=[approved]).results[0]
            assert result.executed
            result = execute_policy_evaluation_with_ledger(db, run_id=run.id,
                evaluation=evaluation, approvals=[wrong_finding]).results[0]
            assert result.status == "blocked" and not result.replayed
            executor.assert_called_once()


def test_batch_duplicate_slots_do_not_execute_twice():
    for changed in (False, True):
        with isolated_ledger() as db:
            run = start_investigation_run(db, 62)
            evaluation = make_evaluation(make_request())
            duplicate = evaluation.results[0].model_copy(deep=True)
            if changed:
                duplicate.tool_request.target = "finding:63"
            evaluation.results.append(duplicate)
            executor = Mock(return_value={"ok": True})
            with patch.dict(TOOL_REGISTRY, {"create_ticket": replace(TOOL_REGISTRY["create_ticket"], executor=executor)}):
                batch = execute_policy_evaluation_with_ledger(db, run_id=run.id,
                    evaluation=evaluation, approvals=[])
            executor.assert_called_once()
            assert batch.simulated_count == 1
            assert batch.replayed_count == (0 if changed else 1)
            assert batch.blocked_count == (1 if changed else 0)
            assert not batch.results[1].executed
            assert len(get_investigation_trace(db, run.id).events) == 2


def test_missing_binding_fingerprint_fails_closed():
    with isolated_ledger() as db:
        run = start_investigation_run(db, 62)
        executor = Mock(return_value={"ok": True})
        with patch.dict(TOOL_REGISTRY, {"create_ticket": replace(TOOL_REGISTRY["create_ticket"], executor=executor)}):
            execute_with_ledger(db, run_id=run.id, request=make_request())
            event = db.query(InvestigationEvent).filter_by(run_id=run.id).one()
            metadata = dict(event.event_metadata)
            metadata.pop("request_fingerprint")
            event.event_metadata = metadata
            db.commit()
            result = execute_with_ledger(db, run_id=run.id, request=make_request()).results[0]
            assert result.status == "blocked" and not result.replayed
            executor.assert_called_once()


def test_failed_slot_rejects_changed_semantics():
    with isolated_ledger() as db:
        run = start_investigation_run(db, 62)
        executor = Mock(side_effect=[RuntimeError("test failure"), {"ok": True}])
        with patch.dict(TOOL_REGISTRY, {"create_ticket": replace(TOOL_REGISTRY["create_ticket"], executor=executor)}):
            first = execute_with_ledger(db, run_id=run.id, request=make_request()).results[0]
            assert first.status == "failed"
            changed = execute_with_ledger(db, run_id=run.id,
                request=make_request(target="finding:63")).results[0]
            assert changed.status == "blocked"
            retry = execute_with_ledger(db, run_id=run.id, request=make_request()).results[0]
            assert retry.executed and retry.execution_intent.attempt == 2
            assert executor.call_count == 2


def test_validation_still_precedes_replay():
    with isolated_ledger() as db:
        run = start_investigation_run(db, 62)
        executor = Mock(return_value={"ok": True})
        with patch.dict(TOOL_REGISTRY, {"create_ticket": replace(TOOL_REGISTRY["create_ticket"], executor=executor)}):
            execute_with_ledger(db, run_id=run.id, request=make_request())
            result = execute_with_ledger(db, run_id=run.id,
                request=make_request(parameters={"unexpected": True})).results[0]
            assert result.status == "blocked" and result.execution_intent is None
            assert not result.replayed
            executor.assert_called_once()



def main():
    checks = (
        test_canonical_request_fingerprint,
        test_same_run_replay_deduplicated,
        test_replay_fingerprint_mismatch_blocked,
        test_different_runs_remain_independent,
        test_approval_before_execution_and_replay,
        test_invalid_parameters_blocked_before_intent,
        test_failed_execution_remains_retryable,
        test_current_authorization_precedes_replay,
        test_approval_is_bound_to_finding_and_parameters,
        test_batch_duplicate_slots_do_not_execute_twice,
        test_missing_binding_fingerprint_fails_closed,
        test_failed_slot_rejects_changed_semantics,
        test_validation_still_precedes_replay,
    )

    for check in checks:
        check()

        print(
            f"[PASS] {check.__name__}"
        )

    print(
        "\nExecution Idempotency "
        "evaluation PASSED"
    )


if __name__ == "__main__":
    main()