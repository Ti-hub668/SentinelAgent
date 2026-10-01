from app.agent.adapters.base import (
    ToolAdapter,
)


class TicketAdapter(
    ToolAdapter
):

    @property
    def name(self):
        return "create_ticket"


    def execute(
        self,
        *,
        parameters: dict,
        dry_run: bool = True,
    ) -> dict:

        if dry_run:
            return {
                "mode": "dry_run",
                "ticket_id": "DRY-TICKET-001",
                "parameters": parameters,
            }

        raise NotImplementedError(
            "Production ticket adapter not configured."
        )