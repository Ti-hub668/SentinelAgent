from dataclasses import dataclass

from pydantic import BaseModel
from app.schemas.tool_capability import ToolCapabilityDescriptor, ToolRiskLevel
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
from app.agent.adapters.base import (
    ToolAdapter,
)
from app.agent.adapters.registry import (
    get_adapter,
)


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
    - governed tool adapter
    """

    name: ResponseActionType

    parameter_schema: type[
        BaseModel
    ]

    adapter: ToolAdapter
    description: str
    risk_level: ToolRiskLevel
    requires_target: bool
    requires_approval: bool
    governance_notes: str
    capabilities: tuple[str, ...]
    tags: tuple[str, ...]

    def describe(self) -> ToolCapabilityDescriptor:
        # Explicit allowlist: never serialize this dataclass or its adapter.
        # Contract docstrings can mention implementation details; omit them.
        def public_schema(value):
            if isinstance(value, dict):
                return {
                    key: public_schema(item)
                    for key, item in value.items()
                    if key != "description"
                }
            if isinstance(value, list):
                return [public_schema(item) for item in value]
            return value

        return ToolCapabilityDescriptor(
            name=self.name,
            description=self.description,
            risk_level=self.risk_level,
            requires_target=self.requires_target,
            requires_approval=self.requires_approval,
            governance_notes=self.governance_notes,
            capabilities=self.capabilities,
            tags=self.tags,
            parameter_contract=self.parameter_schema.__name__,
            parameters_schema=public_schema(self.parameter_schema.model_json_schema()),
        )

    def validate_parameters(self, request: ToolRequest) -> ToolRequest:
        parameters = self.parameter_schema.model_validate(request.parameters)
        return request.model_copy(update={"parameters": parameters.model_dump()})


TOOL_REGISTRY: dict[
    ResponseActionType,
    ToolDefinition,
] = {
    "create_ticket": ToolDefinition(
        name="create_ticket",

        parameter_schema=(
            CreateTicketParameters
        ),

        adapter=get_adapter(
            "create_ticket"
        ),
        description='Simulate a remediation ticket for the supplied target.',
        risk_level='low',
        requires_target=True,
        requires_approval=False,
        governance_notes='Human-review investigations require approval.',
        capabilities=('ticketing',),
        tags=('remediation', "dry_run"),
    ),

    "notify": ToolDefinition(
        name="notify",
        parameter_schema=(
            NotifyParameters
        ),
        adapter=get_adapter("notify"),
        description='Simulate a security notification for the supplied target.',
        risk_level='low',
        requires_target=True,
        requires_approval=False,
        governance_notes='Human-review investigations require approval.',
        capabilities=('notification',),
        tags=('communication', "dry_run"),
    ),

    "block_ip": ToolDefinition(
        name="block_ip",
        parameter_schema=(
            BlockIpParameters
        ),
        adapter=get_adapter("block_ip"),
        description='Simulate network containment for the supplied target.',
        risk_level='high',
        requires_target=True,
        requires_approval=True,
        governance_notes='Requires approval; denied while the investigation requires human review.',
        capabilities=('network_containment',),
        tags=('disruptive', "dry_run"),
    ),

    "manual_review": ToolDefinition(
        name="manual_review",
        parameter_schema=(
            ManualReviewParameters
        ),
        adapter=get_adapter("manual_review"),
        description='Simulate acknowledgement of a human security review.',
        risk_level='low',
        requires_target=True,
        requires_approval=True,
        governance_notes='Always enters the human approval workflow.',
        capabilities=('human_review',),
        tags=('review', "dry_run"),
    ),
}


def get_tool_definition(
    tool_name: str,
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

    return definition.validate_parameters(request)


def list_tool_capabilities() -> list[ToolCapabilityDescriptor]:
    """Return fresh, detached public descriptions in stable name order."""
    return [TOOL_REGISTRY[name].describe() for name in sorted(TOOL_REGISTRY)]


def get_tool_capability(tool_name: str) -> ToolCapabilityDescriptor | None:
    """Unknown names have no capability; discovery does not execute tools."""
    definition = get_tool_definition(tool_name)
    return definition.describe() if definition is not None else None
