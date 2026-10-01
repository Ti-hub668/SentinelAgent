from app.agent.adapters.base import ToolAdapter


class ManualReviewAdapter(ToolAdapter):

    @property
    def name(self) -> str:
        return "manual_review"

    def execute(
        self,
        *,
        parameters: dict,
        dry_run: bool = True,
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