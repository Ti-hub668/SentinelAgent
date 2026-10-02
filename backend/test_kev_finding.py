import json

from app.db.database import SessionLocal

# Load referenced SQLAlchemy models so their tables are
# registered in Base.metadata for this standalone test.
from app.models.asset import Asset
from app.models.scan_task import ScanTask
from app.models.finding import Finding

from app.knowledge_ingestion.kev_lookup import KEVLookup


TEST_CVE = "CVE-2026-7273"


def main():
    db = SessionLocal()

    try:
        # --------------------------------
        # 1. 创建测试 Finding
        # --------------------------------

        finding = Finding(
            scan_task_id=14,
            asset_id=1,
            source="nuclei",
            finding_type="vulnerability",
            title="KEV Integration Test",
            severity="high",
            target="127.0.0.1",
            description="Temporary KEV integration test.",
            evidence="Synthetic integration test evidence.",
            remediation="Test only.",
            template_id=TEST_CVE,
            cve_ids=json.dumps(
                [TEST_CVE],
                ensure_ascii=False,
            ),
            cwe_ids=json.dumps(
                ["CWE-121"],
                ensure_ascii=False,
            ),
            status="open",
            risk_score=80,
            risk_level="high",
            risk_reason="Synthetic integration test.",
        )

        db.add(finding)
        db.commit()
        db.refresh(finding)

        print()
        print("=" * 60)
        print("Finding -> CISA KEV Integration Test")
        print("=" * 60)

        print(f"Finding ID : {finding.id}")
        print(f"CVE JSON   : {finding.cve_ids}")

        # --------------------------------
        # 2. 从数据库字段恢复 CVE IDs
        # --------------------------------

        cve_ids = json.loads(
            finding.cve_ids or "[]"
        )

        print(f"CVE IDs    : {cve_ids}")

        # --------------------------------
        # 3. 查询 CISA KEV
        # --------------------------------

        kev_lookup = KEVLookup()

        for cve_id in cve_ids:
            kev_record = kev_lookup.get(
                cve_id
            )

            print()
            print(f"Query CVE  : {cve_id}")

            if kev_record is None:
                print("In KEV     : NO")
                continue

            print("In KEV     : YES")
            print(
                f"Exploited   : "
                f"{kev_record.known_exploited}"
            )
            print(
                f"Title       : "
                f"{kev_record.title}"
            )
            print(
                f"CWE         : "
                f"{kev_record.cwe_ids}"
            )
            print(
                f"Products    : "
                f"{kev_record.affected_products}"
            )

        print()
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()