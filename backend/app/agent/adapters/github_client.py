"""Minimal secret-safe GitHub Issues REST client."""

import json
from dataclasses import dataclass
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.parse import quote
from urllib.request import (
    Request,
    urlopen,
)

from app.agent.adapters.errors import (
    ToolAdapterResponseError,
    ToolAdapterTransportError,
)
from app.core.tool_settings import (
    GitHubTicketSettings,
)


@dataclass(
    frozen=True,
    slots=True,
)
class GitHubIssue:
    number: int
    html_url: str
    title: str


@dataclass(
    frozen=True,
    slots=True,
)
class GitHubIssueResult:
    issue: GitHubIssue
    created: bool


class GitHubIssueClient:
    def __init__(
        self,
        settings: GitHubTicketSettings,
    ):
        self._settings = settings

    def find_by_execution_id(
        self,
        execution_id: str,
    ) -> GitHubIssue | None:
        marker = (
            f"sentinel-execution:"
            f"{execution_id}"
        )

        query = (
            f"repo:{self._settings.owner}/"
            f"{self._settings.repo} "
            "is:issue "
            "in:body "
            f'"{marker}"'
        )

        path = (
            "/search/issues"
            f"?q={quote(query)}"
        )

        payload = self._request(
            method="GET",
            path=path,
        )

        items = payload.get(
            "items",
            [],
        )

        if not isinstance(
            items,
            list,
        ):
            raise ToolAdapterResponseError(
                "GitHub issue search returned "
                "an unexpected response."
            )

        for item in items:
            if not isinstance(
                item,
                dict,
            ):
                continue

            body = (
                item.get("body")
                or ""
            )

            if (
                isinstance(body, str)
                and marker in body
            ):
                return self._parse_issue(
                    item
                )

        return None

    def create_issue(
        self,
        *,
        title: str,
        body: str,
        execution_id: str,
    ) -> GitHubIssueResult:
        marker = (
            f"sentinel-execution:"
            f"{execution_id}"
        )

        existing = (
            self.find_by_execution_id(
                execution_id
            )
        )

        if existing is not None:
            return GitHubIssueResult(
                issue=existing,
                created=False,
            )

        final_body = (
            f"{body.rstrip()}\n\n"
            "---\n"
            f"{marker}"
        )

        payload = self._request(
            method="POST",
            path=(
                f"/repos/"
                f"{self._settings.owner}/"
                f"{self._settings.repo}/issues"
            ),
            data={
                "title": title,
                "body": final_body,
            },
        )

        return GitHubIssueResult(
            issue=self._parse_issue(
                payload
            ),
            created=True,
        )

    def _request(
        self,
        *,
        method: str,
        path: str,
        data: dict | None = None,
    ) -> dict:
        url = (
            f"{self._settings.api_url}"
            f"{path}"
        )

        body = None

        if data is not None:
            body = json.dumps(
                data
            ).encode(
                "utf-8"
            )

        request = Request(
            url=url,
            data=body,
            method=method,
            headers={
                "Accept": (
                    "application/"
                    "vnd.github+json"
                ),
                "Authorization": (
                    "Bearer "
                    f"{self._settings.token}"
                ),
                "Content-Type": (
                    "application/json"
                ),
                "User-Agent": (
                    "SentinelAgent"
                ),
                "X-GitHub-Api-Version": (
                    "2022-11-28"
                ),
            },
        )

        try:
            with urlopen(
                request,
                timeout=(
                    self._settings
                    .timeout_seconds
                ),
            ) as response:
                raw = response.read()

        except HTTPError as exc:
            raise ToolAdapterResponseError(
                "GitHub API returned "
                f"HTTP {exc.code}."
            ) from exc

        except (
            URLError,
            TimeoutError,
            OSError,
        ) as exc:
            raise ToolAdapterTransportError(
                "GitHub API transport failed."
            ) from exc

        try:
            decoded = json.loads(
                raw.decode(
                    "utf-8"
                )
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise ToolAdapterResponseError(
                "GitHub API returned "
                "an invalid JSON response."
            ) from exc

        if not isinstance(
            decoded,
            dict,
        ):
            raise ToolAdapterResponseError(
                "GitHub API returned "
                "an unexpected response."
            )

        return decoded

    @staticmethod
    def _parse_issue(
        payload: dict,
    ) -> GitHubIssue:
        number = payload.get(
            "number"
        )

        html_url = payload.get(
            "html_url"
        )

        title = payload.get(
            "title"
        )

        if (
            not isinstance(
                number,
                int,
            )
            or not isinstance(
                html_url,
                str,
            )
            or not isinstance(
                title,
                str,
            )
        ):
            raise ToolAdapterResponseError(
                "GitHub issue response "
                "is missing required fields."
            )

        return GitHubIssue(
            number=number,
            html_url=html_url,
            title=title,
        )