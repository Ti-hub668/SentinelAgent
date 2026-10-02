from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ScanCreate(BaseModel):
    asset_id: int

    scan_profile: Literal[
        "fast",
        "security",
        "full",
    ] = "fast"


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


class DiscoveryResponse(BaseModel):
    port_id: int
    scan_task_id: int
    asset_id: int
    host: str
    protocol: str
    port: int
    service: str
    product: str
    version: str
    web_target: str | None
    scan_status: str
    discovered_at: datetime
