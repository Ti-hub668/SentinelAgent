from datetime import datetime

from pydantic import BaseModel


class ScanCreate(BaseModel):
    asset_id: int


class PortResponse(BaseModel):
    id: int
    host: str
    protocol: str
    port: int
    service: str
    product: str
    version: str


class ScanResponse(BaseModel):
    id: int
    asset_id: int
    scanner: str
    status: str
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    ports: list[PortResponse]