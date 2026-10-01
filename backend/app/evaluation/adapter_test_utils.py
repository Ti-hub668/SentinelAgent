from app.agent.adapters.base import ToolAdapter


class TestAdapter(ToolAdapter):
    """Adapter test double wrapping one callable."""

    def __init__(
        self,
        execute_fn,
        *,
        name: str = "create_ticket",
    ):
        self._execute_fn = execute_fn
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def execute(
        self,
        *,
        parameters: dict,
        dry_run: bool = True,
    ) -> dict:
        return self._execute_fn(parameters)