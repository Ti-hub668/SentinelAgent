"""Day45 external Ticket Adapter safety checks."""
import json
import os
from unittest.mock import patch

from app.agent.adapters.errors import (
    ToolAdapterConfigurationError,
)
from app.agent.adapters.ticket import (
    TicketAdapter,
)
from app.agent.adapters.base import (
    ToolExecutionContext,
)
from app.agent.adapters.github_client import (
    GitHubIssue,
    GitHubIssueResult,
)

def test_real_mode_requires_execution_context():
    adapter = TicketAdapter()

    env = {
        "SENTINEL_GITHUB_TICKET_ENABLED":
            "true",
        "SENTINEL_GITHUB_OWNER":
            "example",
        "SENTINEL_GITHUB_REPO":
            "sentinel-test",
        "SENTINEL_GITHUB_TOKEN":
            "fake-secret",
    }

    with patch.dict(
        os.environ,
        env,
        clear=True,
    ):
        try:
            adapter.execute(
                parameters={},
                dry_run=False,
            )

        except ToolAdapterConfigurationError:
            pass

        else:
            raise AssertionError(
                "Real execution was allowed "
                "without execution context."
            )


def test_real_mode_reports_created_ticket():
    adapter = TicketAdapter()

    secret = (
        "github_pat_secret_day45"
    )

    env = {
        "SENTINEL_GITHUB_TICKET_ENABLED":
            "true",
        "SENTINEL_GITHUB_OWNER":
            "example",
        "SENTINEL_GITHUB_REPO":
            "sentinel-test",
        "SENTINEL_GITHUB_TOKEN":
            secret,
    }

    context = ToolExecutionContext(
        execution_id=(
            "exec-day45-created"
        ),
        idempotency_key=(
            "slot-day45-created"
        ),
        run_id=62,
        request_index=0,
        attempt=1,
    )

    issue = GitHubIssue(
        number=123,
        html_url=(
            "https://github.com/"
            "example/sentinel-test/"
            "issues/123"
        ),
        title=(
            "[SentinelAgent] "
            "Security investigation ticket"
        ),
    )

    with patch.dict(
        os.environ,
        env,
        clear=True,
    ):
        with patch(
            "app.agent.adapters.ticket."
            "GitHubIssueClient.create_issue",
            return_value=(
                GitHubIssueResult(
                    issue=issue,
                    created=True,
                )
            ),
        ) as create_issue:
            result = adapter.execute(
                parameters={},
                dry_run=False,
                execution_context=(
                    context
                ),
            )

    assert (
        result["mode"]
        == "real"
    )

    assert (
        result["ticket_created"]
        is True
    )

    assert (
        result["reused_existing"]
        is False
    )

    assert (
        result["ticket_number"]
        == 123
    )

    assert (
        result["execution_id"]
        == "exec-day45-created"
    )

    assert (
        secret
        not in json.dumps(
            result,
            ensure_ascii=False,
        )
    )

    create_issue.assert_called_once()

def test_real_mode_reports_reused_ticket():
    adapter = TicketAdapter()

    secret = (
        "github_pat_secret_day45"
    )

    env = {
        "SENTINEL_GITHUB_TICKET_ENABLED":
            "true",
        "SENTINEL_GITHUB_OWNER":
            "example",
        "SENTINEL_GITHUB_REPO":
            "sentinel-test",
        "SENTINEL_GITHUB_TOKEN":
            secret,
    }

    context = ToolExecutionContext(
        execution_id=(
            "exec-day45-reused"
        ),
        idempotency_key=(
            "slot-day45-reused"
        ),
        run_id=62,
        request_index=0,
        attempt=2,
    )

    issue = GitHubIssue(
        number=123,
        html_url=(
            "https://github.com/"
            "example/sentinel-test/"
            "issues/123"
        ),
        title=(
            "[SentinelAgent] "
            "Security investigation ticket"
        ),
    )

    with patch.dict(
        os.environ,
        env,
        clear=True,
    ):
        with patch(
            "app.agent.adapters.ticket."
            "GitHubIssueClient.create_issue",
            return_value=(
                GitHubIssueResult(
                    issue=issue,
                    created=False,
                )
            ),
        ):
            result = adapter.execute(
                parameters={},
                dry_run=False,
                execution_context=(
                    context
                ),
            )

    assert (
        result["ticket_created"]
        is False
    )

    assert (
        result["reused_existing"]
        is True
    )

    assert (
        result["ticket_number"]
        == 123
    )

    assert (
        secret
        not in json.dumps(
            result,
            ensure_ascii=False,
        )
    )

def test_secret_not_exposed_on_failure():
    adapter = TicketAdapter()

    secret = (
        "github_pat_extremely_secret_day45"
    )

    env = {
        "SENTINEL_GITHUB_TICKET_ENABLED":
            "true",
        "SENTINEL_GITHUB_OWNER":
            "example",
        "SENTINEL_GITHUB_REPO":
            "sentinel-test",
        "SENTINEL_GITHUB_TOKEN":
            secret,
    }

    context = ToolExecutionContext(
        execution_id=(
            "exec-day45-failure"
        ),
        idempotency_key=(
            "slot-day45-failure"
        ),
        run_id=62,
        request_index=0,
        attempt=1,
    )

    with patch.dict(
        os.environ,
        env,
        clear=True,
    ):
        with patch(
            "app.agent.adapters.ticket."
            "GitHubIssueClient.create_issue",
            side_effect=RuntimeError(
                "safe external failure"
            ),
        ):
            try:
                adapter.execute(
                    parameters={},
                    dry_run=False,
                    execution_context=(
                        context
                    ),
                )

            except RuntimeError as exc:
                assert (
                    secret
                    not in str(exc)
                )

            else:
                raise AssertionError(
                    "Expected external "
                    "execution failure."
                )

def test_dry_run_requires_no_credentials():
    adapter = TicketAdapter()

    with patch.dict(
        os.environ,
        {},
        clear=True,
    ):
        result = adapter.execute(
            parameters={},
            dry_run=True,
        )

    assert (
        result["provider"]
        == "github_issues"
    )

    assert (
        result["mode"]
        == "dry_run"
    )

    assert (
        result["ticket_created"]
        is False
    )


def test_real_mode_fails_closed_without_config():
    adapter = TicketAdapter()

    with patch.dict(
        os.environ,
        {},
        clear=True,
    ):
        try:
            adapter.execute(
                parameters={},
                dry_run=False,
            )

        except ToolAdapterConfigurationError:
            pass

        else:
            raise AssertionError(
                "Real ticket execution was "
                "allowed without configuration."
            )


def test_disabled_integration_fails_closed():
    adapter = TicketAdapter()

    env = {
        "SENTINEL_GITHUB_TICKET_ENABLED":
            "false",
        "SENTINEL_GITHUB_OWNER":
            "example",
        "SENTINEL_GITHUB_REPO":
            "sentinel-test",
        "SENTINEL_GITHUB_TOKEN":
            "fake-secret",
    }

    with patch.dict(
        os.environ,
        env,
        clear=True,
    ):
        try:
            adapter.execute(
                parameters={},
                dry_run=False,
            )

        except ToolAdapterConfigurationError:
            pass

        else:
            raise AssertionError(
                "Disabled integration "
                "was allowed to execute."
            )



def main():
    checks = (
        test_dry_run_requires_no_credentials,
        test_real_mode_fails_closed_without_config,
        test_disabled_integration_fails_closed,
        test_real_mode_requires_execution_context,
        test_real_mode_reports_created_ticket,
        test_real_mode_reports_reused_ticket,
        test_secret_not_exposed_on_failure,
    )

    for check in checks:
        check()

        print(
            f"[PASS] {check.__name__}"
        )

    print(
        "\nExternal Ticket Adapter "
        "safety evaluation PASSED"
    )


if __name__ == "__main__":
    main()