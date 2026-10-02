"""Read-only inventory/scan/context regression using an isolated SQLite database.

Run: python -m app.evaluation.discovery_inventory_evaluator
No scanners, external tools or production database writes are performed.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agent.context_builder import build_investigation_context
from app.api.scans import router
from app.db.database import Base, get_db
from app.models.asset import Asset
from app.models.finding import Finding
from app.models.port import Port
from app.models.scan_task import ScanTask


def main():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    tables = [Asset.__table__, ScanTask.__table__, Port.__table__, Finding.__table__]
    Base.metadata.create_all(engine, tables=tables)
    app = FastAPI()
    app.include_router(router)
    with Session(engine) as db:
        def dependency():
            yield db
        app.dependency_overrides[get_db] = dependency
        with TestClient(app) as client, patch("app.api.scans.run_nmap") as nmap, patch("app.api.scans.run_nuclei") as nuclei:
            assert client.get("/api/scans/discovery").json() == []
            origin = datetime(2026, 1, 1, 12)
            db.add_all([Asset(id=i, name=f"asset-{i}", target="127.0.0.1", asset_type="host") for i in (1, 2)])
            db.flush()
            scans = [
                ScanTask(id=1, asset_id=1, status="completed", created_at=origin, finished_at=origin),
                ScanTask(id=2, asset_id=1, status="failed", created_at=origin, started_at=origin+timedelta(days=1)),
                ScanTask(id=3, asset_id=2, status="completed", created_at=origin+timedelta(days=2)),
                ScanTask(id=4, asset_id=1, status="completed", created_at=origin, finished_at=origin+timedelta(days=3)),
                ScanTask(id=5, asset_id=1, status="completed", created_at=origin, finished_at=origin+timedelta(days=3)),
            ]
            db.add_all(scans)
            db.flush()
            observations = [
                (1, 1, "tcp", 80, "http", "old"), (2, 2, "tcp", 80, "http", "new"),
                (3, 2, "udp", 80, "", ""), (4, 3, "tcp", 80, "http", "other asset"),
                (5, 4, "tcp", 443, "https", "older scan tie"),
                (6, 5, "tcp", 443, "https", "older port tie"),
                (7, 5, "tcp", 443, "https", "latest"),
                (8, 3, "tcp", 3306, "mysql", "MySQL"),
            ]
            db.add_all([Port(id=i, scan_task_id=scan, host="127.0.0.1", protocol=proto, port=port,
                             service=service, product=product, version="1")
                        for i, scan, proto, port, service, product in observations])
            db.add(Finding(id=1, scan_task_id=1, asset_id=1, source="nuclei", finding_type="vulnerability",
                           title="Example long finding", severity="info", target="http://127.0.0.1"))
            db.commit()
            counts = [db.scalar(select(func.count()).select_from(model)) for model in (Asset, ScanTask, Port, Finding)]
            before = build_investigation_context(db, 1).model_dump(mode="json")
            result = client.get("/api/scans/discovery")
            assert result.status_code == 200, result.text
            rows = result.json()
            assert [row["port_id"] for row in rows] == [7, 8, 4, 3, 2]
            assert rows[0]["web_target"] == "https://127.0.0.1"
            assert rows[1]["web_target"] is None
            assert rows[-1]["scan_status"] == "failed"
            assert rows[-1]["discovered_at"] == (origin+timedelta(days=1)).isoformat()
            assert rows[1]["discovered_at"] == (origin+timedelta(days=2)).isoformat()
            assert set(rows[0]) == {"port_id", "scan_task_id", "asset_id", "host", "protocol", "port",
                                    "service", "product", "version", "web_target", "scan_status", "discovered_at"}
            assert client.get("/api/scans/discovery").json() == rows
            assert client.get("/api/scans").status_code == 200
            detail = client.get("/api/scans/1")
            assert detail.status_code == 200, detail.text
            assert detail.json()["ports"][0]["id"] == 1
            assert client.get("/api/scans/999999").status_code == 404
            assert client.get("/api/scans/not-an-id").status_code == 422
            assert "/api/scans/discovery" in client.get("/openapi.json").json()["paths"]
            assert before == build_investigation_context(db, 1).model_dump(mode="json")
            assert counts == [db.scalar(select(func.count()).select_from(model)) for model in (Asset, ScanTask, Port, Finding)]
            nmap.assert_not_called()
            nuclei.assert_not_called()
    engine.dispose()
    print("[PASS] Discovery empty/latest/dedup/timestamps/web targets/route ordering")
    print("[PASS] Scan list/detail/404/validation/OpenAPI; Context and database unchanged; no scanner invocation")


if __name__ == "__main__":
    main()
