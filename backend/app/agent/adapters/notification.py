from app.agent.adapters.base import (
    ToolAdapter,
)


class NotificationAdapter(
    ToolAdapter
):

    @property
    def name(self):
        return "notify"


    def execute(
        self,
        *,
        parameters: dict,
        dry_run: bool = True,
    ) -> dict:

        if dry_run:
            return {
                "mode": "dry_run",
                "notification_id":
                    "DRY-NOTIFY-001",
                "parameters":
                    parameters,
            }

        raise NotImplementedError(
            "Production notification adapter not configured."
        )