from abc import ABC, abstractmethod


class ToolAdapter(ABC):
    """
    Unified execution adapter interface.

    Tool Broker should not know
    whether execution is mock,
    API-based, or production.
    """

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
    ) -> dict:
        pass