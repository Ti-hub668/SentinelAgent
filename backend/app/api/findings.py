import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.finding import Finding
from app.schemas.finding import FindingResponse
from app.schemas.ai_analysis import AIAnalysisInput, AIAnalysisResult
from app.ai.two_stage_analyzer import (
    analyze_finding_two_stage,
    TWO_STAGE_ANALYZER_VERSION,
)
from app.models.ai_analysis import AIAnalysis
from app.core.config import settings
from app.schemas.ai_analysis_record import AIAnalysisRecordResponse
from app.rag.query_builder import build_finding_query
from app.rag.retriever import SecurityKnowledgeRetriever
from app.rag.context_builder import build_rag_context
from app.intelligence.structured_enricher import (
    StructuredIntelligenceEnricher,
)

router = APIRouter(
    prefix="/api/findings",
    tags=["Findings"]
)


@router.get("", response_model=list[FindingResponse])
def get_findings(db: Session = Depends(get_db)):
    result = db.execute(
        select(Finding).order_by(Finding.id.desc())
    )

    findings = result.scalars().all()

    return findings


@router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(
    finding_id: int,
    db: Session = Depends(get_db)
):
    finding = db.get(Finding, finding_id)

    if finding is None:
        raise HTTPException(
            status_code=404,
            detail="Finding not found"
        )

    return finding

@router.post(
    "/{finding_id}/analyze",
    response_model=AIAnalysisResult
)
def analyze_finding_endpoint(
    finding_id: int,
    use_rag: bool = True,
    db: Session = Depends(get_db),
):
    finding = db.get(Finding, finding_id)

    if finding is None:
        raise HTTPException(
            status_code=404,
            detail="Finding not found"
        )

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
        risk_score=finding.risk_score,
        risk_level=finding.risk_level,
        risk_reason=finding.risk_reason
    )

    # --------------------------------
    # RAG Retrieval
    # --------------------------------

    rag_context = None
    retrieval_results = []
    rag_top_k = None

    if use_rag:
        rag_top_k = 1

        query = build_finding_query(
            analysis_input
        )

        retriever = SecurityKnowledgeRetriever()

        retrieval_results = retriever.retrieve(
            query=query,
            top_k=rag_top_k,
        )

        rag_context = build_rag_context(
            retrieval_results
        )
    # --------------------------------
    # Structured Intelligence
    # --------------------------------

    structured_intelligence = None

    enricher = StructuredIntelligenceEnricher()

    intelligence_result = enricher.enrich(
        finding
    )

    cve_ids = intelligence_result[
        "identifiers"
    ]["cve_ids"]

    if cve_ids:
        structured_intelligence = json.dumps(
            intelligence_result,
            ensure_ascii=False,
            indent=2,
        )
    # --------------------------------
    # Two-Stage AI Analysis
    # --------------------------------

    evidence_result, enrichment_result = (
        analyze_finding_two_stage(
            analysis_input,
            structured_intelligence=structured_intelligence,
            rag_context=rag_context,
        )
    )

    result = AIAnalysisResult(
        verdict=enrichment_result.final_verdict,
        confidence=enrichment_result.confidence,
        summary=enrichment_result.summary,
        risk_explanation=enrichment_result.risk_explanation,
        recommended_action=enrichment_result.recommended_action,
    )
    # --------------------------------
    # RAG Trace
    # --------------------------------

    retrieved_context = None

    if use_rag:
        retrieved_context = json.dumps(
            [
                {
                    "document_id": item.document.id,
                    "title": item.document.title,
                    "score": round(item.score, 4),
                }
                for item in retrieval_results
            ],
            ensure_ascii=False,
        )

    # --------------------------------
    # LLM Model
    # --------------------------------

    if settings.LLM_PROVIDER == "ollama":
        model_name = settings.OLLAMA_MODEL

    elif settings.LLM_PROVIDER == "openai":
        model_name = settings.OPENAI_MODEL

    else:
        model_name = "unknown"

    # --------------------------------
    # Save AI Analysis
    # --------------------------------
    analysis_record = AIAnalysis(
        finding_id=finding.id,
        provider=settings.LLM_PROVIDER,
        model=model_name,
        prompt_version=TWO_STAGE_ANALYZER_VERSION,

        # Final Analysis
        verdict=result.verdict,
        confidence=result.confidence,
        summary=result.summary,
        risk_explanation=result.risk_explanation,
        recommended_action=result.recommended_action,

        # RAG Trace
        use_rag=use_rag,
        rag_top_k=rag_top_k,
        retrieved_context=retrieved_context,

        # Stage 1 Evidence Assessment Trace
        finding_category=evidence_result.finding_category,
        evidence_status=evidence_result.evidence_status,
        preliminary_verdict=evidence_result.preliminary_verdict,
        evidence_confidence=evidence_result.confidence,
        evidence_reason=evidence_result.reason,

        # Stage 2 Risk Enrichment Trace
        priority=enrichment_result.priority,

        # Structured Intelligence Trace
        structured_intelligence=structured_intelligence,
    )

    db.add(analysis_record)
    db.commit()
    db.refresh(analysis_record)

    return result

@router.get(
    "/{finding_id}/analyses",
    response_model=list[AIAnalysisRecordResponse]
)
def get_finding_analyses(
    finding_id: int,
    db: Session = Depends(get_db)
):
    finding = db.get(Finding, finding_id)

    if finding is None:
        raise HTTPException(
            status_code=404,
            detail="Finding not found"
        )

    result = db.execute(
        select(AIAnalysis)
        .where(AIAnalysis.finding_id == finding_id)
        .order_by(AIAnalysis.id.desc())
    )

    return result.scalars().all()