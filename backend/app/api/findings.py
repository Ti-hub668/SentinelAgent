import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.finding import Finding
from app.schemas.finding import FindingResponse
from app.schemas.ai_analysis import AIAnalysisInput, AIAnalysisResult
from app.ai.risk_analyst import analyze_finding
from app.ai.prompt_builder import PROMPT_VERSION
from app.models.ai_analysis import AIAnalysis
from app.core.config import settings
from app.schemas.ai_analysis_record import AIAnalysisRecordResponse
from app.rag.query_builder import build_finding_query
from app.rag.retriever import SecurityKnowledgeRetriever
from app.rag.context_builder import build_rag_context


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
    # AI Analysis
    # --------------------------------

    result = analyze_finding(
        analysis_input,
        rag_context=rag_context,
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
        prompt_version=PROMPT_VERSION,
        verdict=result.verdict,
        confidence=result.confidence,
        summary=result.summary,
        risk_explanation=result.risk_explanation,
        recommended_action=result.recommended_action,
        use_rag=use_rag,
        rag_top_k=rag_top_k,
        retrieved_context=retrieved_context,
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