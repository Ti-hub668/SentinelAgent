"""Configuration for governed external tool integrations."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitHubTicketSettings:
    enabled: bool
    api_url: str
    owner: str | None
    repo: str | None
    token: str | None
    timeout_seconds: float

    @property
    def configured(self) -> bool:
        return bool(
            self.enabled
            and self.owner
            and self.repo
            and self.token
        )


def get_github_ticket_settings() -> GitHubTicketSettings:
    enabled = (
        os.getenv(
            "SENTINEL_GITHUB_TICKET_ENABLED",
            "false",
        )
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )

    return GitHubTicketSettings(
        enabled=enabled,
        api_url=os.getenv(
            "SENTINEL_GITHUB_API_URL",
            "https://api.github.com",
        ).rstrip("/"),
        owner=(
            os.getenv(
                "SENTINEL_GITHUB_OWNER"
            )
            or None
        ),
        repo=(
            os.getenv(
                "SENTINEL_GITHUB_REPO"
            )
            or None
        ),
        token=(
            os.getenv(
                "SENTINEL_GITHUB_TOKEN"
            )
            or None
        ),
        timeout_seconds=float(
            os.getenv(
                "SENTINEL_GITHUB_TIMEOUT_SECONDS",
                "10",
            )
        ),
    )

def external_tool_execution_enabled() -> bool:
    return os.getenv("SENTINEL_EXTERNAL_TOOL_EXECUTION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def redact_tool_secrets(value):
    """Remove the configured credential from untrusted result/parameter strings."""
    token = os.getenv("SENTINEL_GITHUB_TOKEN")
    if isinstance(value, str):
        return value.replace(token, "[REDACTED]") if token else value
    if isinstance(value, dict):
        return {redact_tool_secrets(k): redact_tool_secrets(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_tool_secrets(v) for v in value]
    return value

def get_execution_claim_stale_seconds() -> int:
    raw = (
        os.getenv(
            "SENTINEL_EXECUTION_CLAIM_STALE_SECONDS",
            "60",
        )
        .strip()
    )

    try:
        value = int(raw)

    except ValueError:
        return 60

    return max(
        value,
        1,
    )