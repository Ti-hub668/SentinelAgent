from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.decision_agent import make_security_decision
from app.db.database import get_db
from app.models.ai_analysis import AIAnalysis
from app.models.agent_decision import AgentDecision
from app.models.finding import Finding
from app.schemas.agent_decision import (
    AgentDecisionInput,
    AgentDecisionOutput,
)


router = APIRouter(
    prefix="/api/agent",
    tags=["agent"],
)

@router.post(
    "/findings/{finding_id}/decision",
    response_model=AgentDecisionOutput,
)
def create_agent_decision(
    finding_id: int,
    db: Session = Depends(get_db),
):
    # 1. 查询 Finding
    finding = (
        db.query(Finding)
        .filter(Finding.id == finding_id)
        .first()
    )

    if finding is None:
        raise HTTPException(
            status_code=404,
            detail="Finding not found",
        )

    # 2. 查询该 Finding 最新一次 AI Analysis
    ai_analysis = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.finding_id == finding_id)
        .order_by(AIAnalysis.id.desc())
        .first()
    )

    if ai_analysis is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "No AI analysis found for this finding. "
                "Run AI analysis first."
            ),
        )

    # 3. 构造 Decision Agent 输入
    decision_input = AgentDecisionInput(
        finding_id=finding.id,
        ai_analysis_id=ai_analysis.id,
        verdict=ai_analysis.verdict,
        confidence=ai_analysis.confidence,
        severity=finding.severity,
        risk_score=finding.risk_score or 0,
        risk_level=finding.risk_level or "low",
    )

    # 4. Decision Agent 做决策
    decision = make_security_decision(decision_input)

    # 5. 保存 Agent Decision
    record = AgentDecision(
        finding_id=finding.id,
        ai_analysis_id=ai_analysis.id,
        action=decision.action,
        priority=decision.priority,
        reason=decision.reason,
        requires_human_review=decision.requires_human_review,
        recommended_next_step=decision.recommended_next_step,
        verdict=ai_analysis.verdict,
        confidence=ai_analysis.confidence,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return decision
@router.get("/decisions")
def list_agent_decisions(
    db: Session = Depends(get_db),
):
    decisions = (
        db.query(AgentDecision)
        .order_by(AgentDecision.id.desc())
        .all()
    )

    return decisions
@router.get("/findings/{finding_id}/decisions")
def list_finding_decisions(
    finding_id: int,
    db: Session = Depends(get_db),
):
    finding = (
        db.query(Finding)
        .filter(Finding.id == finding_id)
        .first()
    )

    if finding is None:
        raise HTTPException(
            status_code=404,
            detail="Finding not found",
        )

    decisions = (
        db.query(AgentDecision)
        .filter(AgentDecision.finding_id == finding_id)
        .order_by(AgentDecision.id.desc())
        .all()
    )

    return decisions