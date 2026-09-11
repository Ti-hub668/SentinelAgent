from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetCreate(BaseModel):
    name: str
    target: str
    asset_type: str


class AssetResponse(BaseModel):
    id: int
    name: str
    target: str
    asset_type: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)