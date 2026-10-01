"""Base abstractions for governed tool adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class ToolExecutionContext:
    """
    Governance metadata supplied to a Tool Adapter.

    This metadata is separate from business parameters.
    Secrets must never be placed here.
    """

    execution_id: str | None = None
    idempotency_key: str | None = None
    request_fingerprint: str | None = None
    run_id: int | None = None
    request_index: int | None = None
    attempt: int | None = None


class ToolAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def execute(
        self,
        *,
        parameters: dict,
        dry_run: bool = True,
        execution_context: ToolExecutionContext | None = None,
    ) -> dict:
        pass