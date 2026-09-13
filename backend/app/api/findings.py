from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.finding import Finding
from app.schemas.finding import FindingResponse
from app.schemas.ai_analysis import AIAnalysisInput, AIAnalysisResult
from app.ai.risk_analyst import analyze_finding


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
    db: Session = Depends(get_db)
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

    result = analyze_finding(analysis_input)

    return result