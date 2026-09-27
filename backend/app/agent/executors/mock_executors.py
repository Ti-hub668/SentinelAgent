from app.schemas.response_plan import ToolRequest


def simulate_create_ticket(
    request: ToolRequest,
) -> dict:
    return {
        "executor": "mock_create_ticket",
        "simulated": True,
        "ticket_id": "SIM-TICKET-001",
        "target": request.target,
        "message": (
            "Ticket creation was simulated. "
            "No external ticket system was modified."
        ),
    }


def simulate_notify(
    request: ToolRequest,
) -> dict:
    return {
        "executor": "mock_notify",
        "simulated": True,
        "target": request.target,
        "message": (
            "Notification delivery was simulated. "
            "No message was sent."
        ),
    }


def simulate_block_ip(
    request: ToolRequest,
) -> dict:
    return {
        "executor": "mock_block_ip",
        "simulated": True,
        "target": request.target,
        "message": (
            "IP blocking was simulated. "
            "No firewall or network control "
            "was changed."
        ),
    }


def simulate_manual_review(
    request: ToolRequest,
) -> dict:
    return {
        "executor": "mock_manual_review",
        "simulated": True,
        "target": request.target,
        "message": (
            "Manual review completion was "
            "acknowledged in dry-run mode."
        ),
    }