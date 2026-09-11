from fastapi import FastAPI

from app.api.assets import router as assets_router
from app.db.database import Base, engine
from app.models.asset import Asset


app = FastAPI(
    title="SentinelAgent",
    description="AI-Powered Security Operations Platform",
    version="0.1.0"
)


Base.metadata.create_all(bind=engine)


app.include_router(assets_router)


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