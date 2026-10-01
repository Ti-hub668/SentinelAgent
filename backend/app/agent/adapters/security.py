from app.agent.adapters.base import (
    ToolAdapter,
    ToolExecutionContext,
)

class SecurityActionAdapter(
    ToolAdapter
):

    @property
    def name(self):
        return "block_ip"


    def execute(
    self,
    *,
    parameters: dict,
    dry_run: bool = True,
    execution_context: ToolExecutionContext | None = None,
) -> dict:
        if dry_run:
            return {
                "mode": "dry_run",
                "action":
                    "block_ip",
                "parameters":
                    parameters,
            }

        raise NotImplementedError(
            "Production security adapter not configured."
        )