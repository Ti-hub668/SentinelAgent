from fastapi import FastAPI

from app.api.scans import router as scans_router
from app.api.assets import router as assets_router
from app.db.database import Base, engine
from app.models.asset import Asset
from app.models.scan_task import ScanTask
from app.models.port import Port
from app.models.vulnerability import Vulnerability
from app.models.finding import Finding
from app.api.vulnerabilities import router as vulnerabilities_router
from app.api.findings import router as findings_router
from app.models.ai_analysis import AIAnalysis

app = FastAPI(
    title="SentinelAgent",
    description="AI-Powered Security Operations Platform",
    version="0.1.0"
)


Base.metadata.create_all(bind=engine)


app.include_router(assets_router)
app.include_router(scans_router)
app.include_router(vulnerabilities_router)
app.include_router(findings_router)

@app.get("/")
def root():
    return {
        "name": "SentinelAgent",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }