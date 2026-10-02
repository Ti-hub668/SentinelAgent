import json

from app.intelligence.structured_enricher import (
    StructuredIntelligenceEnricher,
)
from app.models.finding import Finding


def main():
    # 只创建 Python 对象，不 add / commit 到数据库
    finding = Finding(
        id=999999,
        scan_task_id=1,
        asset_id=1,
        source="nuclei",
        finding_type="vulnerability",
        title="Structured Intelligence Test",
        severity="high",
        target="127.0.0.1",
        description="Synthetic test finding.",
        evidence="Synthetic test evidence.",
        remediation=None,
        template_id="CVE-2026-7273",
        cve_ids=json.dumps(
            ["CVE-2026-7273"]
        ),
        cwe_ids=json.dumps(
            ["CWE-121"]
        ),
        status="open",
        risk_score=80,
        risk_level="high",
        risk_reason="Synthetic test.",
    )

    enricher = StructuredIntelligenceEnricher()

    intelligence = enricher.enrich(
        finding
    )

    print()
    print("=" * 60)
    print("Structured Intelligence Enrichment Test")
    print("=" * 60)

    print(
        json.dumps(
            intelligence,
            ensure_ascii=False,
            indent=2,
        )
    )

    print("=" * 60)


if __name__ == "__main__":
    main()