"""GitHub Issues-backed ticket adapter."""

import json

from app.agent.adapters.base import (
    ToolAdapter,
    ToolExecutionContext,
)
from app.agent.adapters.errors import (
    ToolAdapterConfigurationError,
)
from app.agent.adapters.github_client import (
    GitHubIssueClient,
)
from app.core.tool_settings import (
    GitHubTicketSettings,
    get_github_ticket_settings,
)
from app.schemas.reconciliation import (
    ToolReconciliationResult,
)

class TicketAdapter(ToolAdapter):
    @property
    def name(self) -> str:
        return "create_ticket"

    def execute(
        self,
        *,
        parameters: dict,
        dry_run: bool = True,
        execution_context: ToolExecutionContext | None = None,
    ) -> dict:
        if dry_run:
            return {
                "provider": "github_issues",
                "mode": "dry_run",
                "ticket_created": False,
                "reused_existing": False,
                "parameters": parameters,
            }

        settings = (
            get_github_ticket_settings()
        )

        if not settings.configured:
            raise ToolAdapterConfigurationError(
                "GitHub ticket integration "
                "is not configured or enabled."
            )

        if (
            execution_context
            is None
            or not execution_context.execution_id
        ):
            raise ToolAdapterConfigurationError(
                "External ticket execution "
                "requires an execution context."
            )

        return self._execute_github(
            parameters=parameters,
            execution_context=(
                execution_context
            ),
            settings=settings,
        )

    def reconcile(
        self,
        *,
        execution_context: ToolExecutionContext,
    ) -> ToolReconciliationResult:
        settings = (
            get_github_ticket_settings()
        )

        if not settings.configured:
            raise ToolAdapterConfigurationError(
                "GitHub ticket integration "
                "is not configured or enabled."
            )

        if not execution_context.execution_id:
            raise ToolAdapterConfigurationError(
                "Ticket reconciliation requires "
                "an execution ID."
            )

        execution_id = (
            execution_context.execution_id
        )

        client = GitHubIssueClient(
            settings
        )

        issue = (
            client.find_by_execution_id(
                execution_id
            )
        )

        if issue is None:
            return ToolReconciliationResult(
                state="not_found",
                message=(
                    "No matching external GitHub "
                    "issue was confirmed."
                ),
                output={
                    "provider":
                        "github_issues",
                    "execution_id":
                        execution_id,
                },
            )

        return ToolReconciliationResult(
            state="confirmed_completed",
            message=(
                "Existing GitHub issue confirmed "
                "for the execution ID."
            ),
            output={
                "provider":
                    "github_issues",
                "mode":
                    "real",
                "ticket_created":
                    False,
                "reused_existing":
                    True,
                "ticket_number":
                    issue.number,
                "ticket_url":
                    issue.html_url,
                "execution_id":
                    execution_id,
                "reconciled":
                    True,
            },
        )

    def _execute_github(
        self,
        *,
        parameters: dict,
        execution_context: ToolExecutionContext,
        settings: GitHubTicketSettings,
    ) -> dict:
        client = GitHubIssueClient(
            settings
        )

        execution_id = (
            execution_context.execution_id
        )

        title = (
            "[SentinelAgent] "
            "Security investigation ticket"
        )

        body_lines = [
            (
                "SentinelAgent generated this "
                "security ticket through the "
                "governed Tool Adapter layer."
            ),
            "",
            f"Execution ID: {execution_id}",
        ]

        if (
            execution_context.idempotency_key
            is not None
        ):
            body_lines.append(
                "Idempotency Key: "
                f"{execution_context.idempotency_key}"
            )

        if (
            execution_context.run_id
            is not None
        ):
            body_lines.append(
                "Investigation Run: "
                f"{execution_context.run_id}"
            )

        if (
            execution_context.request_index
            is not None
        ):
            body_lines.append(
                "Request Index: "
                f"{execution_context.request_index}"
            )

        if parameters:
            body_lines.extend(
                [
                    "",
                    "Validated tool parameters:",
                    "```json",
                    json.dumps(
                        parameters,
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    ),
                    "```",
                ]
            )

        result = client.create_issue(
            title=title,
            body="\n".join(
                body_lines
            ),
            execution_id=execution_id,
        )

        issue = result.issue

        return {
            "provider": "github_issues",
            "mode": "real",
            "ticket_created": (
                result.created
            ),
            "reused_existing": (
                not result.created
            ),
            "ticket_number": (
                issue.number
            ),
            "ticket_url": (
                issue.html_url
            ),
            "execution_id": (
                execution_id
            ),
        }