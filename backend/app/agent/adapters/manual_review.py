from app.agent.adapters.base import (
    ToolAdapter,
    ToolExecutionContext,
)

class ManualReviewAdapter(ToolAdapter):

    @property
    def name(self) -> str:
        return "manual_review"

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
                "action": "manual_review",
                "parameters": parameters,
            }

        raise NotImplementedError(
            "Production manual review adapter not configured."
        )