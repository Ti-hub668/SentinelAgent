"""Day44 Tool Adapter Architecture regression checks."""

from dataclasses import replace
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent.adapters.errors import ToolAdapterError
from app.agent.adapters.base import ToolAdapter
from app.agent.adapters.registry import (
    ADAPTER_REGISTRY,
    get_adapter,
)
from app.agent.approval import approve_request
from app.agent.ledger import start_investigation_run
from app.agent.policy_engine import (
    build_approval_requests,
    evaluate_response_plan,
)
from app.agent.tool_broker import (
    execute_policy_evaluation,
    execute_policy_evaluation_with_ledger,
)
from app.agent.tool_registry import (
    TOOL_REGISTRY,
)
from app.evaluation.adapter_test_utils import (
    TestAdapter,
)
from app.evaluation.tool_broker_evaluator import (
    make_plan,
)
from app.models.execution_claim import (
    ExecutionClaim,
)
from app.models.investigation_event import (
    InvestigationEvent,
)
from app.models.investigation_run import (
    InvestigationRun,
)
from app.schemas.response_plan import (
    ToolRequest,
)


EXPECTED_ADAPTERS = {
    "create_ticket",
    "notify",
    "block_ip",
    "manual_review",
}


def make_request(
    tool_name="create_ticket",
    *,
    target="finding:62",
    parameters=None,
):
    if parameters is None:
        parameters = {}

    if (
        tool_name == "manual_review"
        and not parameters
    ):
        parameters = {
            "finding_id": 62,
            "grounded_verdict":
                "likely_true_positive",
        }

    return ToolRequest(
        tool_name=tool_name,
        target=target,
        reason=(
            "Day44 adapter architecture "
            "evaluation."
        ),
        parameters=parameters,
    )


def test_adapter_registry():
    assert (
        set(ADAPTER_REGISTRY)
        == EXPECTED_ADAPTERS
    )

    assert (
        set(TOOL_REGISTRY)
        == EXPECTED_ADAPTERS
    )

    for name in sorted(
        EXPECTED_ADAPTERS
    ):
        adapter = get_adapter(
            name
        )

        definition = (
            TOOL_REGISTRY[
                name
            ]
        )

        assert (
            adapter
            is not None
        )

        assert isinstance(
            adapter,
            ToolAdapter,
        )

        assert (
            definition.adapter
            is adapter
        )

        assert (
            adapter.name
            == name
        )

    assert (
        get_adapter(
            "unknown_tool"
        )
        is None
    )


def test_dry_run_routes_through_adapter():
    spy = Mock(
        return_value={
            "adapter":
                "create_ticket",
            "mode":
                "dry_run",
        }
    )

    definition = (
        TOOL_REGISTRY[
            "create_ticket"
        ]
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket":
                replace(
                    definition,
                    adapter=TestAdapter(
                        spy,
                        name=(
                            "create_ticket"
                        ),
                    ),
                )
        },
    ):
        evaluation = (
            evaluate_response_plan(
                make_plan(
                    request=(
                        make_request()
                    )
                )
            )
        )

        batch = (
            execute_policy_evaluation(
                evaluation,
                approvals=[],
            )
        )

        result = (
            batch.results[
                0
            ]
        )

        assert (
            result.status
            == "simulated"
        )

        assert (
            result.executed
            is True
        )

        assert (
            result.dry_run
            is True
        )

        assert (
            result.output
            == {
                "adapter":
                    "create_ticket",
                "mode":
                    "dry_run",
            }
        )

        spy.assert_called_once()


def test_contract_blocks_before_adapter():
    spy = Mock(
        return_value={
            "unexpected":
                True,
        }
    )

    definition = (
        TOOL_REGISTRY[
            "create_ticket"
        ]
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "create_ticket":
                replace(
                    definition,
                    adapter=TestAdapter(
                        spy,
                        name=(
                            "create_ticket"
                        ),
                    ),
                )
        },
    ):
        evaluation = (
            evaluate_response_plan(
                make_plan(
                    request=(
                        make_request(
                            parameters={
                                "dangerous_option":
                                    True
                            }
                        )
                    )
                )
            )
        )

        batch = (
            execute_policy_evaluation(
                evaluation,
                approvals=[],
            )
        )

        result = (
            batch.results[
                0
            ]
        )

        assert (
            result.status
            == "blocked"
        )

        assert (
            result.executed
            is False
        )

        spy.assert_not_called()


def test_policy_blocks_before_adapter():
    spy = Mock(
        return_value={
            "should_not_run":
                True,
        }
    )

    definition = (
        TOOL_REGISTRY[
            "block_ip"
        ]
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "block_ip":
                replace(
                    definition,
                    adapter=TestAdapter(
                        spy,
                        name="block_ip",
                    ),
                )
        },
    ):
        plan = make_plan(
            request=(
                make_request(
                    "block_ip",
                    target=(
                        "192.0.2.10"
                    ),
                )
            ),
            requires_human_review=True,
        )

        evaluation = (
            evaluate_response_plan(
                plan
            )
        )

        assert (
            evaluation.results[
                0
            ].decision
            == "DENY"
        )

        batch = (
            execute_policy_evaluation(
                evaluation,
                approvals=[],
            )
        )

        assert (
            batch.results[
                0
            ].status
            == "blocked"
        )

        spy.assert_not_called()


def test_approval_blocks_before_adapter():
    spy = Mock(
        return_value={
            "action":
                "block_ip",
            "mode":
                "dry_run",
        }
    )

    definition = (
        TOOL_REGISTRY[
            "block_ip"
        ]
    )

    with patch.dict(
        TOOL_REGISTRY,
        {
            "block_ip":
                replace(
                    definition,
                    adapter=TestAdapter(
                        spy,
                        name="block_ip",
                    ),
                )
        },
    ):
        evaluation = (
            evaluate_response_plan(
                make_plan(
                    request=(
                        make_request(
                            "block_ip",
                            target=(
                                "192.0.2.10"
                            ),
                        )
                    )
                )
            )
        )

        assert (
            evaluation.results[
                0
            ].decision
            == "REQUIRE_APPROVAL"
        )

        approvals = (
            build_approval_requests(
                evaluation
            )
        )

        pending = (
            execute_policy_evaluation(
                evaluation,
                approvals=approvals,
            )
        )

        assert (
            pending.results[
                0
            ].status
            == "blocked"
        )

        spy.assert_not_called()

        approved = (
            approve_request(
                approvals[0],
                reviewer=(
                    "day44-evaluator"
                ),
                reason=(
                    "Approved for "
                    "dry-run adapter test."
                ),
            )
        )

        executed = (
            execute_policy_evaluation(
                evaluation,
                approvals=[
                    approved
                ],
            )
        )

        assert (
            executed.results[
                0
            ].status
            == "simulated"
        )

        spy.assert_called_once()


def test_claim_and_replay_do_not_double_invoke():
    engine = create_engine(
        "sqlite:///:memory:"
    )

    InvestigationRun.__table__.create(
        engine
    )

    InvestigationEvent.__table__.create(
        engine
    )

    ExecutionClaim.__table__.create(
        engine
    )

    spy = Mock(
        return_value={
            "ticket":
                "DAY44-001",
        }
    )

    definition = (
        TOOL_REGISTRY[
            "create_ticket"
        ]
    )

    try:
        with patch.dict(
            TOOL_REGISTRY,
            {
                "create_ticket":
                    replace(
                        definition,
                        adapter=TestAdapter(
                            spy,
                            name=(
                                "create_ticket"
                            ),
                        ),
                    )
            },
        ):
            with Session(
                engine
            ) as db:
                run = (
                    start_investigation_run(
                        db,
                        62,
                    )
                )

                evaluation = (
                    evaluate_response_plan(
                        make_plan(
                            request=(
                                make_request()
                            )
                        )
                    )
                )

                first = (
                    execute_policy_evaluation_with_ledger(
                        db,
                        run_id=run.id,
                        evaluation=(
                            evaluation
                        ),
                        approvals=[],
                    )
                )

                second = (
                    execute_policy_evaluation_with_ledger(
                        db,
                        run_id=run.id,
                        evaluation=(
                            evaluation
                        ),
                        approvals=[],
                    )
                )

                first_result = (
                    first.results[
                        0
                    ]
                )

                second_result = (
                    second.results[
                        0
                    ]
                )

                assert (
                    first_result.status
                    == "simulated"
                )

                assert (
                    first_result.executed
                    is True
                )

                assert (
                    second_result.replayed
                    is True
                )

                assert (
                    second_result.executed
                    is False
                )

                assert (
                    second_result.output
                    == {
                        "ticket":
                            "DAY44-001"
                    }
                )

                spy.assert_called_once()

                claim = (
                    db.query(
                        ExecutionClaim
                    )
                    .filter(
                        ExecutionClaim.run_id
                        == run.id
                    )
                    .one()
                )

                assert (
                    claim.status
                    == "completed"
                )

    finally:
        engine.dispose()


def test_builtin_adapters_fail_closed_without_production_config():
    for name in sorted(
        EXPECTED_ADAPTERS
    ):
        adapter = get_adapter(
            name
        )

        try:
            adapter.execute(
                parameters={},
                dry_run=False,
            )

        except (
            ToolAdapterError,
            NotImplementedError,
            ValueError,
        ):
            pass

        else:
            raise AssertionError(
                f"{name} unexpectedly "
                "allowed production execution"
            )


def main():
    checks = (
        test_adapter_registry,
        test_dry_run_routes_through_adapter,
        test_contract_blocks_before_adapter,
        test_policy_blocks_before_adapter,
        test_approval_blocks_before_adapter,
        test_claim_and_replay_do_not_double_invoke,
        test_builtin_adapters_fail_closed_without_production_config,
    )

    for check in checks:
        check()

        print(
            f"[PASS] "
            f"{check.__name__}"
        )

    print(
        "\nTool Adapter evaluation PASSED"
    )


if __name__ == "__main__":
    main()