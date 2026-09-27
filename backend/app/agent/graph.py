from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agent.context_builder import (
    build_investigation_context,
)
from app.agent.state import SentinelInvestigationState
from app.agent.tools.intelligence_tool import (
    lookup_context_intelligence,
)
from app.agent.tools.rag_tool import (
    retrieve_context_knowledge,
)
from app.agent.grounding_validator import (
    validate_grounding,
)
from app.ai.two_stage_analyzer import (
    analyze_finding_two_stage,
)
from app.schemas.ai_analysis import AIAnalysisInput
from app.db.database import SessionLocal
from collections.abc import Callable

def safe_node(
    node_name: str,
    node_func: Callable[
        [SentinelInvestigationState],
        dict,
    ],
):
    """
    Wrap a LangGraph node with a consistent fail-safe boundary.

    Node failures are converted into structured workflow state
    instead of crashing the entire investigation immediately.
    """

    def wrapped(
        state: SentinelInvestigationState,
    ) -> dict:
        try:
            return node_func(state)

        except Exception as exc:
            return {
                "status": "failed",
                "failed_node": node_name,
                "error": (
                    f"{type(exc).__name__}: {exc}"
                ),
            }

    return wrapped

def build_context_node(
    state: SentinelInvestigationState,
) -> dict:
    """
    Load deterministic investigation context from MySQL.
    """

    db = SessionLocal()

    try:
        context = build_investigation_context(
            db,
            finding_id=state["finding_id"],
        )

        return {
            "context": context,
            "status": "context_built",
            "error": None,
        }

    finally:
        db.close()


def triage_node(
    state: SentinelInvestigationState,
) -> dict:
    """
    Perform deterministic investigation triage.

    Triage decides whether additional RAG / intelligence
    research is useful before deeper analysis.
    """

    context = state.get("context")

    if context is None:
        raise RuntimeError(
            "Investigation context is missing."
        )

    finding = context.finding

    signals: list[str] = []

    # Explicit vulnerability identifiers
    if finding.cve_ids:
        signals.append(
            "CVE identifiers are present."
        )

    if finding.cwe_ids:
        signals.append(
            "CWE identifiers are present."
        )

    # Scanner template metadata
    if finding.template_id:
        signals.append(
            "Scanner template metadata is available."
        )

    # Higher-severity findings
    if finding.severity.lower() in {
        "medium",
        "high",
        "critical",
    }:
        signals.append(
            "Finding severity warrants additional research."
        )

    # Deterministic risk signal
    if (
        context.deterministic_risk.risk_score
        is not None
        and context.deterministic_risk.risk_score
        >= 40
    ):
        signals.append(
            "Deterministic risk score warrants research."
        )

    needs_research = bool(signals)

    if needs_research:
        triage_reason = " ".join(signals)

    else:
        triage_reason = (
            "No explicit vulnerability identifier, scanner "
            "template, elevated severity, or elevated risk "
            "signal requires additional research."
        )

    return {
        "needs_research": needs_research,
        "triage_reason": triage_reason,
        "status": "triage_completed",
        "error": None,
    }

def research_node(
    state: SentinelInvestigationState,
) -> dict:
    """
    Run SentinelAgent typed security research tools.

    Research enriches the investigation context with:
    1. RAG security knowledge
    2. Structured vulnerability intelligence
    """

    context = state.get("context")

    if context is None:
        raise RuntimeError(
            "Investigation context is missing."
        )

    rag_result = retrieve_context_knowledge(
        context,
        top_k=3,
    )

    intelligence_result = (
        lookup_context_intelligence(
            context
        )
    )

    return {
        "rag_result": rag_result,
        "intelligence_result": intelligence_result,
        "status": "research_completed",
        "error": None,
    }


def analyze_node(
    state: SentinelInvestigationState,
) -> dict:
    """
    Run SentinelAgent's existing two-stage AI analysis.

    Stage 1:
        Finding evidence only
        -> Evidence Assessment

    Stage 2:
        Evidence Assessment
        + optional RAG
        + optional structured intelligence
        -> Risk Enrichment
    """

    context = state.get("context")

    if context is None:
        raise RuntimeError(
            "Investigation context is missing."
        )

    finding = context.finding

    analysis_input = AIAnalysisInput(
        finding_id=finding.id,
        source=finding.source,
        finding_type=finding.finding_type,
        title=finding.title,
        severity=finding.severity,
        target=finding.target,
        description=finding.description,
        evidence=finding.evidence,
        remediation=finding.remediation,
        risk_score=(
            context.deterministic_risk.risk_score
        ),
        risk_level=(
            context.deterministic_risk.risk_level
        ),
        risk_reason=(
            context.deterministic_risk.risk_reason
        ),
    )

    rag_result = state.get(
        "rag_result"
    )

    intelligence_result = state.get(
        "intelligence_result"
    )

    rag_context = None

    if rag_result is not None:
        rag_context = rag_result.prompt_context

    structured_intelligence = None

    if intelligence_result is not None:
        structured_intelligence = (
            intelligence_result.model_dump_json(
                indent=2
            )
        )

    (
        evidence_result,
        enrichment_result,
    ) = analyze_finding_two_stage(
        analysis_input,
        structured_intelligence=(
            structured_intelligence
        ),
        rag_context=rag_context,
    )

    return {
        "evidence_assessment": evidence_result,
        "risk_enrichment": enrichment_result,
        "status": "analysis_completed",
        "error": None,
    }

def grounding_node(
    state: SentinelInvestigationState,
) -> dict:
    """
    Validate whether AI conclusions are grounded
    in investigation evidence and intelligence.
    """

    grounding_result = validate_grounding(
        state
    )

    return {
        "grounding_result": grounding_result,
        "status": "grounding_completed",
        "error": None,
    }

def route_after_triage(
    state: SentinelInvestigationState,
) -> Literal[
    "research",
    "analyze",
]:
    """
    Route after deterministic triage.

    Research is optional, but every Finding must still
    enter the two-stage analysis pipeline.
    """

    if state.get(
        "needs_research",
        False,
    ):
        return "research"

    return "analyze"

def route_after_node(
    state: SentinelInvestigationState,
) -> Literal[
    "continue",
    "end",
]:
    """
    Stop the workflow safely when a previous node failed.
    """

    if state.get("status") == "failed":
        return "end"

    return "continue"

def build_investigation_graph():
    """
    Build SentinelAgent investigation workflow.
    """

    builder = StateGraph(
        SentinelInvestigationState
    )

    builder.add_node(
    "build_context",
        safe_node(
            "build_context",
            build_context_node,
        ),
    )

    builder.add_node(
        "triage",
        safe_node(
            "triage",
            triage_node,
        ),
    )

    builder.add_node(
        "research",
        safe_node(
            "research",
            research_node,
        ),
    )

    builder.add_node(
        "analyze",
        safe_node(
            "analyze",
            analyze_node,
        ),
    )

    builder.add_node(
    "grounding",
        safe_node(
            "grounding",
            grounding_node,
        ),
    )

    builder.add_edge(
        START,
        "build_context",
    )

    builder.add_conditional_edges(
        "build_context",
        route_after_node,
        {
            "continue": "triage",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "research": "research",
            "analyze": "analyze",
        },
    )

    builder.add_conditional_edges(
        "research",
        route_after_node,
        {
            "continue": "analyze",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "analyze",
        route_after_node,
        {
            "continue": "grounding",
            "end": END,
        },
    )

    builder.add_edge(
        "grounding",
        END,
    )

    return builder.compile()


investigation_graph = build_investigation_graph()