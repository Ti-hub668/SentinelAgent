from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from app.schemas.response_plan import ResponseActionType


ToolRiskLevel = Literal["low", "medium", "high"]


class ToolCapabilityDescriptor(BaseModel):
    """Public planning data only; metadata never grants authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: ResponseActionType
    description: str = Field(min_length=1)
    risk_level: ToolRiskLevel
    requires_target: bool
    requires_approval: bool = Field(
        description="Baseline guidance only; Policy Engine may require approval or deny."
    )
    governance_notes: str = Field(min_length=1)
    capabilities: tuple[str, ...] = Field(min_length=1)
    tags: tuple[str, ...] = Field(min_length=1)
    dry_run: Literal[True] = True
    parameter_contract: str = Field(min_length=1)
    parameters_schema: dict[str, JsonValue]


class ToolRegistryAuditMetadata(BaseModel):
    """Snapshot at dispatch; null validated_contract means validation did not pass."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: ResponseActionType
    risk_level: ToolRiskLevel
    parameter_contract: str
    validated_contract: str | None = None
