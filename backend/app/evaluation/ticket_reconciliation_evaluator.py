import os
from unittest.mock import patch

from app.agent.adapters.base import (
    ToolExecutionContext,
)
from app.agent.adapters.errors import (
    ToolAdapterConfigurationError,
)
from app.agent.adapters.github_client import (
    GitHubIssue,
)
from app.agent.adapters.ticket import (
    TicketAdapter,
)


TEST_ENV = {
    "SENTINEL_GITHUB_TICKET_ENABLED":
        "true",
    "SENTINEL_GITHUB_OWNER":
        "example",
    "SENTINEL_GITHUB_REPO":
        "sentinel-test",
    "SENTINEL_GITHUB_TOKEN":
        "github_pat_day46_secret",
}


def make_context(
    execution_id: str
    = "exec-day46-reconcile-001",
) -> ToolExecutionContext:
    return ToolExecutionContext(
        execution_id=execution_id,
        idempotency_key=(
            "slot-day46-reconcile-001"
        ),
        request_fingerprint=(
            "fingerprint-day46"
        ),
        run_id=46,
        request_index=0,
        attempt=1,
    )


def test_confirmed_external_issue():
    adapter = TicketAdapter()

    issue = GitHubIssue(
        number=321,
        html_url=(
            "https://github.com/"
            "example/sentinel-test/"
            "issues/321"
        ),
        title=(
            "[SentinelAgent] "
            "Security investigation ticket"
        ),
    )

    with patch.dict(
        os.environ,
        TEST_ENV,
        clear=True,
    ):
        with patch(
            "app.agent.adapters.ticket."
            "GitHubIssueClient."
            "find_by_execution_id",
            return_value=issue,
        ) as find_issue:
            with patch(
                "app.agent.adapters.ticket."
                "GitHubIssueClient."
                "create_issue",
            ) as create_issue:
                result = adapter.reconcile(
                    execution_context=(
                        make_context()
                    )
                )

    assert (
        result.state
        == "confirmed_completed"
    )

    assert (
        result.output[
            "ticket_number"
        ]
        == 321
    )

    assert (
        result.output[
            "reconciled"
        ]
        is True
    )

    assert (
        result.output[
            "ticket_created"
        ]
        is False
    )

    find_issue.assert_called_once_with(
        "exec-day46-reconcile-001"
    )

    create_issue.assert_not_called()


def test_external_issue_not_found():
    adapter = TicketAdapter()

    with patch.dict(
        os.environ,
        TEST_ENV,
        clear=True,
    ):
        with patch(
            "app.agent.adapters.ticket."
            "GitHubIssueClient."
            "find_by_execution_id",
            return_value=None,
        ):
            with patch(
                "app.agent.adapters.ticket."
                "GitHubIssueClient."
                "create_issue",
            ) as create_issue:
                result = adapter.reconcile(
                    execution_context=(
                        make_context()
                    )
                )

    assert (
        result.state
        == "not_found"
    )

    assert (
        result.output[
            "execution_id"
        ]
        == "exec-day46-reconcile-001"
    )

    create_issue.assert_not_called()


def test_reconciliation_requires_config():
    adapter = TicketAdapter()

    with patch.dict(
        os.environ,
        {},
        clear=True,
    ):
        try:
            adapter.reconcile(
                execution_context=(
                    make_context()
                )
            )

        except ToolAdapterConfigurationError:
            pass

        else:
            raise AssertionError(
                "Reconciliation unexpectedly "
                "accepted missing GitHub config."
            )


def test_secret_not_returned():
    adapter = TicketAdapter()

    secret = (
        TEST_ENV[
            "SENTINEL_GITHUB_TOKEN"
        ]
    )

    issue = GitHubIssue(
        number=322,
        html_url=(
            "https://github.com/"
            "example/sentinel-test/"
            "issues/322"
        ),
        title="Test",
    )

    with patch.dict(
        os.environ,
        TEST_ENV,
        clear=True,
    ):
        with patch(
            "app.agent.adapters.ticket."
            "GitHubIssueClient."
            "find_by_execution_id",
            return_value=issue,
        ):
            result = adapter.reconcile(
                execution_context=(
                    make_context(
                        "exec-day46-secret"
                    )
                )
            )

    payload = (
        result.model_dump_json()
    )

    assert (
        secret
        not in payload
    )


def main():
    checks = (
        test_confirmed_external_issue,
        test_external_issue_not_found,
        test_reconciliation_requires_config,
        test_secret_not_returned,
    )

    for check in checks:
        check()

        print(
            f"[PASS] {check.__name__}"
        )

    print(
        "\nTicket reconciliation "
        "evaluation PASSED"
    )


if __name__ == "__main__":
    main()