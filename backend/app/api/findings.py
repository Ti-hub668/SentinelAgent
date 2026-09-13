from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.finding import Finding
from app.schemas.finding import FindingResponse


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