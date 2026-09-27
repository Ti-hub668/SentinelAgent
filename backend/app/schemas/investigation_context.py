from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FindingContext(BaseModel):
    id: int
    scan_task_id: int
    asset_id: int

    source: str
    finding_type: str
    title: str
    severity: str
    target: str

    description: str | None = None
    evidence: str | None = None
    remediation: str | None = None

    template_id: str | None = None
    cve_ids: str | None = None
    cwe_ids: str | None = None

    status: str
    created_at: datetime


class AssetContext(BaseModel):
    id: int
    name: str
    target: str
    asset_type: str
    status: str
    created_at: datetime


class ScanTaskContext(BaseModel):
    id: int
    asset_id: int

    scanner: str
    status: str
    error_message: str | None = None

    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class PortContext(BaseModel):
    id: int
    scan_task_id: int

    host: str
    protocol: str
    port: int

    service: str
    product: str
    version: str


class RelatedFindingContext(BaseModel):
    id: int
    scan_task_id: int

    title: str
    severity: str
    status: str

    template_id: str | None = None

    risk_score: int | None = None
    risk_level: str | None = None

    created_at: datetime


class DeterministicRiskContext(BaseModel):
    risk_score: int | None = None
    risk_level: str | None = None
    risk_reason: str | None = None


class SentinelContextBundle(BaseModel):
    """
    Structured investigation context prepared before
    the LangGraph investigation workflow begins.
    """

    finding_id: int

    finding: FindingContext

    asset: AssetContext

    scan_task: ScanTaskContext

    open_ports: list[PortContext] = Field(
        default_factory=list
    )

    related_findings: list[RelatedFindingContext] = Field(
        default_factory=list
    )

    deterministic_risk: DeterministicRiskContext

    # Day21+ will enrich these through typed security tools.
    cve_information: list[dict[str, Any]] = Field(
        default_factory=list
    )

    rag_knowledge: list[dict[str, Any]] = Field(
        default_factory=list
    )