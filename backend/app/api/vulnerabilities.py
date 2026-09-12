from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.vulnerability import Vulnerability
from app.schemas.vulnerability import VulnerabilityResponse


router = APIRouter(
    prefix="/api/vulnerabilities",
    tags=["Vulnerabilities"]
)


@router.get(
    "",
    response_model=list[VulnerabilityResponse]
)
def get_vulnerabilities(
    db: Session = Depends(get_db)
):

    result = db.execute(
        select(Vulnerability)
        .order_by(Vulnerability.id.desc())
    )

    return result.scalars().all()