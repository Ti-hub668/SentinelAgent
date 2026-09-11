from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetResponse


router = APIRouter(
    prefix="/api/assets",
    tags=["Assets"]
)


@router.post("", response_model=AssetResponse)
def create_asset(
    asset_data: AssetCreate,
    db: Session = Depends(get_db)
):
    asset = Asset(
        name=asset_data.name,
        target=asset_data.target,
        asset_type=asset_data.asset_type
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)

    return asset


@router.get("", response_model=list[AssetResponse])
def get_assets(
    db: Session = Depends(get_db)
):
    result = db.execute(
        select(Asset).order_by(Asset.id.desc())
    )

    return result.scalars().all()