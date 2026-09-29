from sqlalchemy.orm import Session

from app.agent.graph import investigation_graph
from app.agent.ledger import (
    complete_investigation_run,
    fail_investigation_run,
    record_investigation_event,
    start_investigation_run,
)
from app.agent.state import SentinelInvestigationState
from app.schemas.investigation_ledger import (
    InvestigationRunRecord,
)


def run_investigation_with_ledger(
    db: Session,
    finding_id: int,
) -> tuple[
    SentinelInvestigationState,
    InvestigationRunRecord,
]:
    """
    Execute one LangGraph investigation and persist
    an auditable investigation trace.
    """

    run = start_investigation_run(
        db,
        finding_id,
    )

    try:
        result = investigation_graph.invoke(
            {
                "finding_id": finding_id,
                "status": "pending",
            }
        )

        # Context
        context = result.get("context")

        if context is not None:
            record_investigation_event(
                db,
                run_id=run.id,
                event_type="context_built",
                node_name="build_context",
                summary=(
                    "Investigation context "
                    "successfully built."
                ),
                event_metadata={
                    "finding_id": finding_id,
                    "asset_id": (
                        context.finding.asset_id
                    ),
                    "scan_task_id": (
                        context.finding.scan_task_id
                    ),
                    "port_count": len(
                        context.open_ports
                    ),
                    "related_finding_count": len(
                        context.related_findings
                    ),
                },
            )
        # Triage
        if "needs_research" in result:
            record_investigation_event(
                db,
                run_id=run.id,
                event_type="triage_completed",
                node_name="triage",
                summary=(
                    "Investigation triage "
                    "completed."
                ),
                event_metadata={
                    "needs_research": result.get(
                        "needs_research"
                    ),
                    "triage_reason": result.get(
                        "triage_reason"
                    ),
                },
            )

        # Research
        rag_result = result.get(
            "rag_result"
        )

        intelligence_result = result.get(
            "intelligence_result"
        )

        if (
            rag_result is not None
            or intelligence_result is not None
        ):
            rag_evidence = []

            if rag_result is not None:
                rag_evidence = [
                    item.model_dump(
                        mode="json"
                    )
                    for item
                    in rag_result.evidence
                ]

            research_metadata = {
                "rag_used": (
                    rag_result
                    is not None
                ),

                "intelligence_used": (
                    intelligence_result
                    is not None
                ),

                "rag_query": (
                    rag_result.query
                    if rag_result
                    is not None
                    else None
                ),

                "rag_index_path": (
                    rag_result.index_path
                    if rag_result
                    is not None
                    else None
                ),

                "retrieval_strategy": (
                    rag_result.retrieval_strategy
                    if rag_result
                    is not None
                    else None
                ),

                "top_k": (
                    rag_result.top_k
                    if rag_result
                    is not None
                    else None
                ),

                "retrieved_sources": (
                    rag_result.retrieved_sources
                    if rag_result
                    is not None
                    else []
                ),

                "retrieved_count": (
                    len(
                        rag_result.results
                    )
                    if rag_result
                    is not None
                    else 0
                ),

                "evidence": (
                    rag_evidence
                ),

                "intelligence": (
                    {
                        "template_id": (
                            intelligence_result
                            .template_id
                        ),

                        "cve_ids": (
                            intelligence_result
                            .cve_ids
                        ),

                        "cwe_ids": (
                            intelligence_result
                            .cwe_ids
                        ),

                        "kev_matched": (
                            intelligence_result
                            .kev_matched
                        ),

                        "kev_record_count": (
                            len(
                                intelligence_result
                                .kev_records
                            )
                        ),

                        "nvd_matched": (
                            intelligence_result
                            .nvd_matched
                        ),

                        "nvd_record_count": (
                            len(
                                intelligence_result
                                .nvd_records
                            )
                        ),
                    }
                    if intelligence_result
                    is not None
                    else None
                ),
            }

            record_investigation_event(
                db,
                run_id=run.id,
                event_type="research_completed",
                node_name="research",
                summary=(
                    "Security research tools "
                    "completed with auditable "
                    "evidence provenance."
                ),
                event_metadata=(
                    research_metadata
                ),
            )

        # Evidence Assessment
        evidence = result.get(
            "evidence_assessment"
        )

        if evidence is not None:
            record_investigation_event(
                db,
                run_id=run.id,
                event_type="evidence_assessed",
                node_name="analyze",
                summary=(
                    "Finding evidence "
                    "assessment completed."
                ),
                event_metadata={
                    "evidence_status": (
                        evidence.evidence_status
                    ),
                    "preliminary_verdict": (
                        evidence.preliminary_verdict
                    ),
                    "confidence": (
                        evidence.confidence
                    ),
                },
            )

        # Risk Enrichment
        enrichment = result.get(
            "risk_enrichment"
        )

        if enrichment is not None:
            record_investigation_event(
                db,
                run_id=run.id,
                event_type="risk_enriched",
                node_name="analyze",
                summary=(
                    "Risk synthesis completed."
                ),
                event_metadata={
                    "priority": (
                        enrichment.priority
                    ),
                    "confidence": (
                        enrichment.confidence
                    ),
                    "final_verdict": (
                        enrichment.final_verdict
                    ),
                },
            )

        # Grounding
        grounding = result.get(
            "grounding_result"
        )

        if grounding is not None:
            record_investigation_event(
                db,
                run_id=run.id,
                event_type="grounding_validated",
                node_name="grounding",
                summary=(
                    "Final analysis passed "
                    "through grounding validation."
                ),
                event_metadata={
                    "grounding_status": (
                        grounding.status
                    ),
                    "grounding_score": (
                        grounding.score
                    ),
                    "original_verdict": (
                        grounding.original_verdict
                    ),
                    "grounded_verdict": (
                        grounding.grounded_verdict
                    ),
                    "requires_human_review": (
                        grounding.requires_human_review
                    ),
                },
            )

        # Graph-level failure
        if result.get("status") == "failed":
            error_message = (
                result.get("error")
                or "Unknown investigation failure."
            )

            record_investigation_event(
                db,
                run_id=run.id,
                event_type="investigation_failed",
                node_name=result.get(
                    "failed_node"
                ),
                status="failed",
                summary=error_message,
            )

            failed_run = fail_investigation_run(
                db,
                run_id=run.id,
                error_message=error_message,
            )

            return result, failed_run

        # Successful completion
        final_verdict = (
            grounding.grounded_verdict
            if grounding is not None
            else (
                enrichment.final_verdict
                if enrichment is not None
                else "unknown"
            )
        )

        completed_run = (
            complete_investigation_run(
                db,
                run_id=run.id,
                final_verdict=final_verdict,
            )
        )

        return result, completed_run

    except Exception as exc:
        error_message = (
            f"{type(exc).__name__}: {exc}"
        )

        try:
            record_investigation_event(
                db,
                run_id=run.id,
                event_type="investigation_failed",
                node_name="runner",
                status="failed",
                summary=error_message,
            )

            failed_run = fail_investigation_run(
                db,
                run_id=run.id,
                error_message=error_message,
            )

        except Exception:
            db.rollback()
            raise

        return (
            {
                "finding_id": finding_id,
                "status": "failed",
                "failed_node": "runner",
                "error": error_message,
            },
            failed_run,
        )