from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.finding import Finding
from app.models.port import Port
from app.models.scan_task import ScanTask

from app.schemas.investigation_context import (
    AssetContext,
    DeterministicRiskContext,
    FindingContext,
    PortContext,
    RelatedFindingContext,
    ScanTaskContext,
    SentinelContextBundle,
)


DEFAULT_RELATED_FINDING_LIMIT = 10


def build_investigation_context(
    db: Session,
    finding_id: int,
    related_limit: int = DEFAULT_RELATED_FINDING_LIMIT,
) -> SentinelContextBundle:
    """
    Build the deterministic investigation context for one Finding.

    This function only collects existing SentinelAgent database facts.
    It does not call LLMs, RAG, threat intelligence, or external tools.
    """

    # ---------------------------------------------------------
    # 1. Finding
    # ---------------------------------------------------------

    finding = db.execute(
        select(Finding).where(
            Finding.id == finding_id
        )
    ).scalar_one_or_none()

    if finding is None:
        raise ValueError(
            f"Finding not found: {finding_id}"
        )

    # ---------------------------------------------------------
    # 2. Asset
    # ---------------------------------------------------------

    asset = db.execute(
        select(Asset).where(
            Asset.id == finding.asset_id
        )
    ).scalar_one_or_none()

    if asset is None:
        raise RuntimeError(
            f"Asset {finding.asset_id} referenced by "
            f"Finding {finding.id} was not found."
        )

    # ---------------------------------------------------------
    # 3. Scan Task
    # ---------------------------------------------------------

    scan_task = db.execute(
        select(ScanTask).where(
            ScanTask.id == finding.scan_task_id
        )
    ).scalar_one_or_none()

    if scan_task is None:
        raise RuntimeError(
            f"ScanTask {finding.scan_task_id} referenced by "
            f"Finding {finding.id} was not found."
        )

    # ---------------------------------------------------------
    # 4. Ports discovered during the same scan
    # ---------------------------------------------------------

    ports = db.execute(
        select(Port)
        .where(
            Port.scan_task_id == finding.scan_task_id
        )
        .order_by(
            Port.port.asc()
        )
    ).scalars().all()

    # ---------------------------------------------------------
    # 5. Other findings on the same asset
    # ---------------------------------------------------------

    related_findings = db.execute(
        select(Finding)
        .where(
            Finding.asset_id == finding.asset_id,
            Finding.id != finding.id,
        )
        .order_by(
            Finding.created_at.desc()
        )
        .limit(related_limit)
    ).scalars().all()

    # ---------------------------------------------------------
    # 6. Build typed context
    # ---------------------------------------------------------

    return SentinelContextBundle(
        finding_id=finding.id,

        finding=FindingContext(
            id=finding.id,
            scan_task_id=finding.scan_task_id,
            asset_id=finding.asset_id,
            source=finding.source,
            finding_type=finding.finding_type,
            title=finding.title,
            severity=finding.severity,
            target=finding.target,
            description=finding.description,
            evidence=finding.evidence,
            remediation=finding.remediation,
            template_id=finding.template_id,
            cve_ids=finding.cve_ids,
            cwe_ids=finding.cwe_ids,
            status=finding.status,
            created_at=finding.created_at,
        ),

        asset=AssetContext(
            id=asset.id,
            name=asset.name,
            target=asset.target,
            asset_type=asset.asset_type,
            status=asset.status,
            created_at=asset.created_at,
        ),

        scan_task=ScanTaskContext(
            id=scan_task.id,
            asset_id=scan_task.asset_id,
            scanner=scan_task.scanner,
            status=scan_task.status,
            error_message=scan_task.error_message,
            created_at=scan_task.created_at,
            started_at=scan_task.started_at,
            finished_at=scan_task.finished_at,
        ),

        open_ports=[
            PortContext(
                id=port.id,
                scan_task_id=port.scan_task_id,
                host=port.host,
                protocol=port.protocol,
                port=port.port,
                service=port.service,
                product=port.product,
                version=port.version,
            )
            for port in ports
        ],

        related_findings=[
            RelatedFindingContext(
                id=item.id,
                scan_task_id=item.scan_task_id,
                title=item.title,
                severity=item.severity,
                status=item.status,
                template_id=item.template_id,
                risk_score=item.risk_score,
                risk_level=item.risk_level,
                created_at=item.created_at,
            )
            for item in related_findings
        ],

        deterministic_risk=DeterministicRiskContext(
            risk_score=finding.risk_score,
            risk_level=finding.risk_level,
            risk_reason=finding.risk_reason,
        ),

        cve_information=[],
        rag_knowledge=[],
    )