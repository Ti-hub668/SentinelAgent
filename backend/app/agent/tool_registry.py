from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from app.agent.executors.mock_executors import (
    simulate_block_ip,
    simulate_create_ticket,
    simulate_manual_review,
    simulate_notify,
)
from app.schemas.response_plan import (
    ResponseActionType,
    ToolRequest,
)
from app.schemas.tool_contracts import (
    BlockIpParameters,
    CreateTicketParameters,
    ManualReviewParameters,
    NotifyParameters,
)


ToolExecutor = Callable[
    [ToolRequest],
    dict,
]


@dataclass(
    frozen=True,
    slots=True,
)
class ToolDefinition:
    """
    One registered Tool Broker capability.

    A tool definition binds together:
    - tool name
    - accepted parameter contract
    - dry-run executor
    """

    name: ResponseActionType

    parameter_schema: type[
        BaseModel
    ]

    executor: ToolExecutor


TOOL_REGISTRY: dict[
    ResponseActionType,
    ToolDefinition,
] = {
    "create_ticket": ToolDefinition(
        name="create_ticket",
        parameter_schema=(
            CreateTicketParameters
        ),
        executor=simulate_create_ticket,
    ),

    "notify": ToolDefinition(
        name="notify",
        parameter_schema=(
            NotifyParameters
        ),
        executor=simulate_notify,
    ),

    "block_ip": ToolDefinition(
        name="block_ip",
        parameter_schema=(
            BlockIpParameters
        ),
        executor=simulate_block_ip,
    ),

    "manual_review": ToolDefinition(
        name="manual_review",
        parameter_schema=(
            ManualReviewParameters
        ),
        executor=simulate_manual_review,
    ),
}


def get_tool_definition(
    tool_name: ResponseActionType,
) -> ToolDefinition | None:
    """
    Resolve one registered tool.

    Missing definitions must fail closed inside
    Tool Broker.
    """

    return TOOL_REGISTRY.get(
        tool_name
    )


def validate_tool_request_parameters(
    request: ToolRequest,
) -> ToolRequest:
    """
    Validate and normalize ToolRequest parameters
    using the registered parameter contract.

    The returned request contains only validated
    parameters.
    """

    definition = get_tool_definition(
        request.tool_name
    )

    if definition is None:
        raise LookupError(
            "No registered tool definition exists "
            f"for {request.tool_name}."
        )

    validated_parameters = (
        definition.parameter_schema
        .model_validate(
            request.parameters
        )
    )

    return request.model_copy(
        update={
            "parameters":
                validated_parameters
                .model_dump(),
        }
    )