"""Day43 durable claims against independent sessions and a real SQL database.

Default: temporary file-backed SQLite. --mysql: configured application MySQL,
creates missing claim table and retains synthetic runs for audit (dry-run only).
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Event, Lock
from unittest.mock import Mock, patch

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.agent.execution_claims import acquire_claim, finish_claim
from app.agent.ledger import start_investigation_run
from app.agent.tool_broker import execute_policy_result
from app.agent.tool_registry import TOOL_REGISTRY
from app.evaluation.execution_idempotency_evaluator import (
    execute_with_ledger,
    make_evaluation,
    make_request,
)
from app.models.execution_claim import ExecutionClaim
from app.models.investigation_event import InvestigationEvent
from app.models.investigation_run import InvestigationRun
from app.evaluation.adapter_test_utils import TestAdapter


@contextmanager
def database(mysql=False):
    if mysql:
        from app.db.database import engine

        ExecutionClaim.__table__.create(
            engine,
            checkfirst=True,
        )
        yield engine
    else:
        with TemporaryDirectory(
            prefix="sentinel-day43-"
        ) as directory:
            engine = create_engine(
                f"sqlite:///{Path(directory) / 'claims.db'}",
                connect_args={
                    "timeout": 15,
                },
            )

            @event.listens_for(
                engine,
                "connect",
            )
            def enforce_foreign_keys(
                connection,
                _,
            ):
                connection.execute(
                    "PRAGMA foreign_keys=ON"
                )

            for model in (
                InvestigationRun,
                InvestigationEvent,
                ExecutionClaim,
            ):
                model.__table__.create(
                    engine
                )

            try:
                yield engine
            finally:
                engine.dispose()


def new_run(engine):
    with Session(engine) as db:
        return start_investigation_run(
            db,
            62,
        ).id


def invoke(
    engine,
    run_id,
    request=None,
):
    with Session(engine) as db:
        return execute_with_ledger(
            db,
            run_id=run_id,
            request=(
                request
                or make_request()
            ),
        ).results[0]


def concurrent_workers(
    engine,
    run_id,
):
    start = Barrier(2)
    loser_done = Event()
    entered = Event()
    mutex = Lock()
    calls = []

    def execute_fn(_):
        with mutex:
            calls.append(1)

        entered.set()

        assert loser_done.wait(
            15
        ), (
            "Contender must return while "
            "winner is still executing"
        )

        return {
            "ticket": "one-only",
        }

    def worker():
        start.wait(
            timeout=15
        )

        result = invoke(
            engine,
            run_id,
        )

        if not result.executed:
            loser_done.set()

        return result

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=TestAdapter(
                    execute_fn
                ),
            )
        },
    ):
        with ThreadPoolExecutor(
            max_workers=2
        ) as pool:
            futures = [
                pool.submit(
                    worker
                )
                for _ in range(2)
            ]

            results = [
                future.result(
                    timeout=30
                )
                for future in futures
            ]

        assert (
            entered.is_set()
            and len(calls) == 1
        )

        assert sorted(
            item.status
            for item in results
        ) == [
            "blocked",
            "simulated",
        ]

        assert any(
            "in_progress"
            in item.message
            for item in results
        )

        replay = invoke(
            engine,
            run_id,
        )

        assert replay.replayed

        assert replay.output == {
            "ticket": "one-only",
        }

        conflict = invoke(
            engine,
            run_id,
            make_request(
                target="finding:63"
            ),
        )

        assert (
            conflict.status
            == "blocked"
        )

        assert (
            "fingerprint"
            in conflict.message
        )

        assert len(calls) == 1

    with Session(engine) as db:
        claim = db.scalar(
            select(
                ExecutionClaim
            ).where(
                ExecutionClaim.run_id
                == run_id
            )
        )

        ledger = db.get(
            InvestigationEvent,
            claim.event_id,
        )

        assert (
            claim.status
            == "completed"
        )

        assert (
            claim.receipt
            ==
            ledger.event_metadata[
                "execution_receipt"
            ]
        )

    return results


def test_two_workers_one_executor(
    engine,
):
    concurrent_workers(
        engine,
        new_run(engine),
    )


def test_concurrent_retry(
    engine,
):
    run_id = new_run(
        engine
    )

    failing_execute = Mock(
        side_effect=RuntimeError(
            "confirmed dry-run failure"
        )
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=TestAdapter(
                    failing_execute
                ),
            )
        },
    ):
        first = invoke(
            engine,
            run_id,
        )

        assert (
            first.status
            == "failed"
        )

        assert (
            first.execution_intent.attempt
            == 1
        )

    results = concurrent_workers(
        engine,
        run_id,
    )

    winner = next(
        item
        for item in results
        if item.executed
    )

    assert (
        winner.execution_intent.attempt
        == 2
    )


def test_retry_budget(
    engine,
):
    run_id = new_run(
        engine
    )

    execute_mock = Mock(
        side_effect=RuntimeError(
            "dry-run failure"
        )
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=TestAdapter(
                    execute_mock
                ),
            )
        },
    ):
        for attempt in range(
            1,
            4,
        ):
            result = invoke(
                engine,
                run_id,
            )

            assert (
                result.status
                == "failed"
            )

            assert (
                result.execution_intent.attempt
                == attempt
            )

        assert (
            invoke(
                engine,
                run_id,
            ).status
            == "blocked"
        )

        assert (
            execute_mock.call_count
            == 3
        )


def test_atomic_receipt_rollback(
    engine,
):
    run_id = new_run(
        engine
    )

    execute_mock = Mock(
        return_value={
            "ok": True,
        }
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=TestAdapter(
                    execute_mock
                ),
            )
        },
    ):
        # Failure AFTER event flush and claim UPDATE,
        # but BEFORE COMMIT.
        def fail_after_update(
            *args,
            **kwargs,
        ):
            finish_claim(
                *args,
                **kwargs,
            )

            raise RuntimeError(
                "injected persistence failure"
            )

        with patch(
            "app.agent.tool_broker.finish_claim",
            side_effect=fail_after_update,
        ):
            try:
                invoke(
                    engine,
                    run_id,
                )

            except RuntimeError as exc:
                assert (
                    "injected"
                    in str(exc)
                )

            else:
                raise AssertionError(
                    "Persistence error "
                    "was swallowed"
                )

        with Session(
            engine
        ) as db:
            claim = db.scalar(
                select(
                    ExecutionClaim
                ).where(
                    ExecutionClaim.run_id
                    == run_id
                )
            )

            assert (
                claim.status
                == "claimed"
            )

            assert (
                claim.receipt
                is None
            )

            assert (
                claim.event_id
                is None
            )

            assert not db.scalars(
                select(
                    InvestigationEvent
                ).where(
                    InvestigationEvent.run_id
                    == run_id
                )
            ).all()

        assert (
            invoke(
                engine,
                run_id,
            ).status
            == "blocked"
        )

        execute_mock.assert_called_once()


def test_stale_owner_cannot_complete(
    engine,
):
    run_id = new_run(
        engine
    )

    failing_execute = Mock(
        side_effect=RuntimeError(
            "dry-run failure"
        )
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=TestAdapter(
                    failing_execute
                ),
            )
        },
    ):
        failed = invoke(
            engine,
            run_id,
        )

    intent = (
        failed.execution_intent
    )

    with Session(
        engine
    ) as db:
        claim = db.scalar(
            select(
                ExecutionClaim
            ).where(
                ExecutionClaim.run_id
                == run_id
            )
        )

        stale_token = (
            claim.owner_token
        )

        current = acquire_claim(
            db,
            intent,
        )

        assert (
            current.state
            == "acquired"
        )

        assert (
            current.attempt
            == 2
        )

        for token, attempt in (
            (
                stale_token,
                1,
            ),
            (
                stale_token,
                2,
            ),
            (
                current.owner_token,
                1,
            ),
        ):
            try:
                finish_claim(
                    db,
                    intent.model_copy(
                        update={
                            "attempt":
                                attempt
                        }
                    ),
                    token,
                    status="completed",
                    receipt={},
                    output={},
                    event_id=(
                        claim.event_id
                        or 0
                    ),
                )

            except RuntimeError:
                db.rollback()

            else:
                raise AssertionError(
                    "Stale owner/attempt "
                    "completed claim"
                )

        assert (
            acquire_claim(
                db,
                intent,
            ).state
            == "in_progress"
        )


def test_legacy_completed_import(
    engine,
):
    run_id = new_run(
        engine
    )

    execute_mock = Mock(
        return_value={
            "old": True,
        }
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=TestAdapter(
                    execute_mock
                ),
            )
        },
    ):
        with Session(
            engine
        ) as db:
            # Offline result recorded as a
            # pre-Day43 event without a claim.
            from app.agent.execution_guard import (
                build_execution_intent,
                build_execution_receipt,
                build_idempotency_key,
                build_request_fingerprint,
            )

            from app.agent.tool_broker import (
                _record_tool_result,
            )

            policy = make_evaluation(
                make_request()
            ).results[0]

            result = (
                execute_policy_result(
                    policy,
                    finding_id=62,
                    approvals=[],
                )
            )

            intent = (
                build_execution_intent(
                    finding_id=62,
                    run_id=run_id,
                    policy_result=policy,
                    validated_request=(
                        result.tool_request
                    ),
                    approval=None,
                    attempt=1,
                    request_fingerprint=(
                        build_request_fingerprint(
                            result.tool_request
                        )
                    ),
                    idempotency_key=(
                        build_idempotency_key(
                            run_id=run_id,
                            request_index=0,
                        )
                    ),
                )
            )

            result.execution_intent = (
                intent
            )

            result.execution_receipt = (
                build_execution_receipt(
                    intent=intent,
                    outcome="simulated",
                    executor_invoked=True,
                )
            )

            _record_tool_result(
                db,
                run_id=run_id,
                result=result,
            )

        assert invoke(
            engine,
            run_id,
        ).replayed

        execute_mock.assert_called_once()

        with Session(
            engine
        ) as db:
            claim = db.scalar(
                select(
                    ExecutionClaim
                ).where(
                    ExecutionClaim.run_id
                    == run_id
                )
            )

            assert (
                claim.status
                == "completed"
            )

            assert (
                claim.output
                == {
                    "old": True,
                }
            )


def test_acquisition_failure_never_executes(
    engine,
):
    run_id = new_run(
        engine
    )

    execute_mock = Mock(
        return_value={
            "ok": True,
        }
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=TestAdapter(
                    execute_mock
                ),
            )
        },
    ):
        with Session(
            engine
        ) as db:
            with patch.object(
                db,
                "commit",
                side_effect=RuntimeError(
                    "claim storage unavailable"
                ),
            ):
                try:
                    execute_with_ledger(
                        db,
                        run_id=run_id,
                        request=make_request(),
                    )

                except RuntimeError as exc:
                    assert (
                        "storage unavailable"
                        in str(exc)
                    )

                else:
                    raise AssertionError(
                        "Failed acquisition "
                        "was accepted"
                    )

        execute_mock.assert_not_called()

    with Session(
        engine
    ) as db:
        assert not db.scalars(
            select(
                ExecutionClaim
            ).where(
                ExecutionClaim.run_id
                == run_id
            )
        ).all()


def test_claimed_conflict_and_no_timeout_takeover(
    engine,
):
    run_id = new_run(
        engine
    )

    execute_mock = Mock(
        return_value={
            "ok": True,
        }
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket": replace(
                TOOL_REGISTRY[
                    "create_ticket"
                ],
                adapter=TestAdapter(
                    execute_mock
                ),
            )
        },
    ):
        with patch(
            "app.agent.tool_broker.finish_claim",
            side_effect=RuntimeError(
                "crash"
            ),
        ):
            try:
                invoke(
                    engine,
                    run_id,
                )

            except RuntimeError:
                pass

        from datetime import datetime

        with Session(
            engine
        ) as db:
            claim = db.scalar(
                select(
                    ExecutionClaim
                ).where(
                    ExecutionClaim.run_id
                    == run_id
                )
            )

            claim.updated_at = (
                datetime(
                    2000,
                    1,
                    1,
                )
            )

            db.commit()

        assert (
            "in_progress"
            in invoke(
                engine,
                run_id,
            ).message
        )

        conflict = invoke(
            engine,
            run_id,
            make_request(
                target="finding:63"
            ),
        )

        assert (
            conflict.status
            == "blocked"
        )

        assert (
            "fingerprint"
            in conflict.message
        )

        execute_mock.assert_called_once()


def main():
    parser = (
        argparse.ArgumentParser(
            description=__doc__
        )
    )

    parser.add_argument(
        "--mysql",
        action="store_true",
    )

    args = parser.parse_args()

    checks = (
        test_two_workers_one_executor,
        test_concurrent_retry,
        test_retry_budget,
        test_atomic_receipt_rollback,
        test_stale_owner_cannot_complete,
        test_legacy_completed_import,
        test_acquisition_failure_never_executes,
        test_claimed_conflict_and_no_timeout_takeover,
    )

    with database(
        args.mysql
    ) as engine:
        for check in checks:
            check(engine)

            print(
                f"[PASS] "
                f"{check.__name__} "
                f"({engine.dialect.name})"
            )

    print(
        "Execution Claim evaluation PASSED"
    )


if __name__ == "__main__":
    main()