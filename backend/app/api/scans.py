from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.asset import Asset
from app.models.port import Port
from app.models.scan_task import ScanTask
from app.schemas.scan import ScanCreate, ScanResponse
from app.scanners.nmap_scanner import run_nmap


router = APIRouter(
    prefix="/api/scans",
    tags=["Scans"]
)


@router.post("", response_model=ScanResponse)
def create_scan(
    scan_data: ScanCreate,
    db: Session = Depends(get_db)
):
    # 1. 根据 asset_id 查询资产
    asset = db.get(Asset, scan_data.asset_id)

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )

    # 2. 创建扫描任务
    scan_task = ScanTask(
        asset_id=asset.id,
        scanner="nmap",
        status="running",
        started_at=datetime.now()
    )

    db.add(scan_task)
    db.commit()
    db.refresh(scan_task)

    try:
        # 3. 调用 Nmap
        scan_results = run_nmap(asset.target)

        # 4. 保存扫描发现的端口
        for result in scan_results:
            port = Port(
                scan_task_id=scan_task.id,
                host=result["host"],
                protocol=result["protocol"],
                port=result["port"],
                service=result["service"],
                product=result["product"],
                version=result["version"]
            )

            db.add(port)

        # 5. 更新任务状态
        scan_task.status = "completed"
        scan_task.finished_at = datetime.now()

        db.commit()

    except Exception as e:
        db.rollback()

        # rollback 后重新获取任务
        scan_task = db.get(ScanTask, scan_task.id)

        scan_task.status = "failed"
        scan_task.error_message = str(e)
        scan_task.finished_at = datetime.now()

        db.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {str(e)}"
        )

    # 6. 查询刚刚保存的端口
    result = db.execute(
        select(Port).where(
            Port.scan_task_id == scan_task.id
        )
    )

    ports = result.scalars().all()

    # 7. 返回结果
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


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db)
):
    # 查询扫描任务
    scan_task = db.get(ScanTask, scan_id)

    if scan_task is None:
        raise HTTPException(
            status_code=404,
            detail="Scan task not found"
        )

    # 查询对应端口
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