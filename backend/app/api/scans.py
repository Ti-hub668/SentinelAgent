from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.asset import Asset
from app.models.port import Port
from app.models.scan_task import ScanTask
from app.models.vulnerability import Vulnerability
from app.models.finding import Finding
from app.schemas.scan import ScanCreate, ScanResponse
from app.scanners.nmap_scanner import run_nmap
from app.scanners.nuclei_scanner import run_nuclei
from app.scanners.web_discovery import build_web_targets
from app.security.risk_analyzer import calculate_risk

router = APIRouter(
    prefix="/api/scans",
    tags=["Scans"]
)


@router.post("", response_model=ScanResponse)
def create_scan(
    scan_data: ScanCreate,
    db: Session = Depends(get_db)
):
    asset = db.get(
        Asset,
        scan_data.asset_id
    )

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )

    scan_task = ScanTask(
        asset_id=asset.id,
        scanner="nmap+nuclei",
        status="running",
        started_at=datetime.now()
    )

    db.add(scan_task)
    db.commit()
    db.refresh(scan_task)

    scan_task_id = scan_task.id

    try:
        # 1. Nmap 扫描
        scan_results = run_nmap(
            asset.target
        )

        # 2. 保存端口
        for result in scan_results:
            port = Port(
                scan_task_id=scan_task_id,
                host=result["host"],
                protocol=result["protocol"],
                port=result["port"],
                service=result["service"],
                product=result["product"],
                version=result["version"]
            )

            db.add(port)

        db.commit()

        # 3. 根据端口生成 Web URL
        web_targets = build_web_targets(
            scan_results
        )

        # 4. 对 Web 服务运行 Nuclei
        for target in web_targets:
            nuclei_results = run_nuclei(
                target
            )

            # 5. 保存漏洞
        for nuclei_finding in nuclei_results:
            vulnerability = Vulnerability(
                scan_task_id=scan_task_id,
                target=nuclei_finding["target"],
                template_id=nuclei_finding["template_id"],
                name=nuclei_finding["name"],
                severity=nuclei_finding["severity"],
                matched_at=nuclei_finding["matched_at"],
                description=nuclei_finding["description"],
                remediation=nuclei_finding["remediation"]
            )

            db.add(vulnerability)

            risk = calculate_risk(
                severity=nuclei_finding["severity"],
                finding_type="vulnerability",
                source="nuclei",
                title=nuclei_finding["name"],
                evidence=nuclei_finding["matched_at"]
            )

            security_finding = Finding(
                scan_task_id=scan_task_id,
                asset_id=asset.id,
                source="nuclei",
                finding_type="vulnerability",
                title=nuclei_finding["name"],
                severity=nuclei_finding["severity"],
                target=nuclei_finding["target"],
                description=nuclei_finding["description"],
                evidence=nuclei_finding["matched_at"],
                remediation=nuclei_finding["remediation"],
                status="open",
                risk_score=risk["risk_score"],
                risk_level=risk["risk_level"],
                risk_reason=risk["risk_reason"]
            )

            db.add(security_finding)

        db.commit()

        # 6. 标记扫描完成
        scan_task = db.get(
            ScanTask,
            scan_task_id
        )

        scan_task.status = "completed"
        scan_task.finished_at = datetime.now()

        db.commit()

    except Exception as e:
        db.rollback()

        scan_task = db.get(
            ScanTask,
            scan_task_id
        )

        if scan_task is not None:
            scan_task.status = "failed"
            scan_task.error_message = str(e)
            scan_task.finished_at = datetime.now()

            db.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {str(e)}"
        )

    # 7. 查询端口结果
    result = db.execute(
        select(Port).where(
            Port.scan_task_id == scan_task_id
        )
    )

    ports = result.scalars().all()

    scan_task = db.get(
        ScanTask,
        scan_task_id
    )

    return {
        "id": scan_task.id,
        "asset_id": scan_task.asset_id,
        "scanner": scan_task.scanner,
        "status": scan_task.status,
        "error_message": scan_task.error_message,
        "created_at": scan_task.created_at,
        "started_at": scan_task.started_at,
        "finished_at": scan_task.finished_at,
        "ports": ports
    }


@router.get(
    "/{scan_id}",
    response_model=ScanResponse
)
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db)
):
    scan_task = db.get(
        ScanTask,
        scan_id
    )

    if scan_task is None:
        raise HTTPException(
            status_code=404,
            detail="Scan task not found"
        )

    result = db.execute(
        select(Port).where(
            Port.scan_task_id == scan_id
        )
    )

    ports = result.scalars().all()

    return {
        "id": scan_task.id,
        "asset_id": scan_task.asset_id,
        "scanner": scan_task.scanner,
        "status": scan_task.status,
        "error_message": scan_task.error_message,
        "created_at": scan_task.created_at,
        "started_at": scan_task.started_at,
        "finished_at": scan_task.finished_at,
        "ports": ports
    }