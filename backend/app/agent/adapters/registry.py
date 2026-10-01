from app.agent.adapters.ticket import (
    TicketAdapter,
)
from app.agent.adapters.notification import (
    NotificationAdapter,
)
from app.agent.adapters.security import (
    SecurityActionAdapter,
)
from app.agent.adapters.manual_review import (
    ManualReviewAdapter,
)

ADAPTER_REGISTRY = {
    "create_ticket":
        TicketAdapter(),

    "notify":
        NotificationAdapter(),

    "block_ip":
        SecurityActionAdapter(),

    "manual_review":
        ManualReviewAdapter(),
}


def get_adapter(
    tool_name: str
):
    return ADAPTER_REGISTRY.get(
        tool_name
    )