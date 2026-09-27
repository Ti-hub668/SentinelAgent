from typing import NotRequired, TypedDict

from app.schemas.agent_tools import (
    RAGToolResult,
    VulnerabilityIntelligenceResult,
)
from app.schemas.evidence_assessment import (
    EvidenceAssessmentResult,
)
from app.schemas.investigation_context import (
    SentinelContextBundle,
)
from app.schemas.risk_enrichment import (
    RiskEnrichmentResult,
)
from app.schemas.grounding import (
    GroundingResult,
)

class SentinelInvestigationState(TypedDict):
    """
    Shared state passed between SentinelAgent LangGraph nodes.
    """

    finding_id: int

    # Context
    context: NotRequired[SentinelContextBundle]

    # Triage
    needs_research: NotRequired[bool]
    triage_reason: NotRequired[str]

    # Research
    rag_result: NotRequired[RAGToolResult]

    intelligence_result: NotRequired[
        VulnerabilityIntelligenceResult
    ]

    # Two-stage AI analysis
    evidence_assessment: NotRequired[
        EvidenceAssessmentResult
    ]

    risk_enrichment: NotRequired[
        RiskEnrichmentResult
    ]

    # Grounding validation
    grounding_result: NotRequired[
        GroundingResult
    ]
    # Workflow
    status: NotRequired[str]

    failed_node: NotRequired[str | None]

    error: NotRequired[str | None]