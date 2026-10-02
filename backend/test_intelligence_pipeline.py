import json

from app.models.finding import Finding
from app.schemas.ai_analysis import AIAnalysisInput
from app.intelligence.structured_enricher import (
    StructuredIntelligenceEnricher,
)
from app.ai.prompt_builder import (
    build_risk_analysis_prompt,
)


def main():
    # Synthetic Finding:
    # 仅用于集成测试，不写入数据库
    finding = Finding(
        id=999999,
        scan_task_id=1,
        asset_id=1,
        source="nuclei",
        finding_type="vulnerability",
        title="CVE Intelligence Pipeline Test",
        severity="high",
        target="127.0.0.1",
        description="Synthetic integration test.",
        evidence="Synthetic scanner evidence.",
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
        risk_reason="Synthetic test risk.",
    )

    # 1. Structured Intelligence Enrichment
    enricher = StructuredIntelligenceEnricher()

    intelligence_result = enricher.enrich(
        finding
    )

    assert intelligence_result[
        "cisa_kev"
    ]["matched"] is True

    records = intelligence_result[
        "cisa_kev"
    ]["records"]

    assert len(records) > 0

    assert records[0][
        "cve_id"
    ] == "CVE-2026-7273"

    assert records[0][
        "known_exploited"
    ] is True

    # 2. Convert structured intelligence to JSON context
    structured_context = json.dumps(
        intelligence_result,
        ensure_ascii=False,
        indent=2,
    )

    # 3. Build AI input
    analysis_input = AIAnalysisInput(
        finding_id=finding.id,
        source=finding.source,
        finding_type=finding.finding_type,
        title=finding.title,
        severity=finding.severity,
        target=finding.target,
        description=finding.description,
        evidence=finding.evidence,
        remediation=finding.remediation,
        risk_score=finding.risk_score,
        risk_level=finding.risk_level,
        risk_reason=finding.risk_reason,
    )

    # 4. Build final prompt
    prompt = build_risk_analysis_prompt(
        analysis_input,
        structured_intelligence=structured_context,
    )

    # 5. Verify intelligence reached the prompt
    assert "五、结构化安全情报" in prompt
    assert "CVE-2026-7273" in prompt
    assert '"known_exploited": true' in prompt
    assert "Zyxel" in prompt

    print("=" * 60)
    print("Structured Intelligence Pipeline Test: PASS")
    print("=" * 60)

    print("Finding CVE:")
    print(
        intelligence_result[
            "identifiers"
        ]["cve_ids"]
    )

    print()

    print("CISA KEV Matched:")
    print(
        intelligence_result[
            "cisa_kev"
        ]["matched"]
    )

    print()

    print("Known Exploited:")
    print(
        records[0][
            "known_exploited"
        ]
    )

    print()

    print("KEV Title:")
    print(
        records[0][
            "title"
        ]
    )

    print()

    print(
        "Structured Intelligence successfully "
        "reached the AI prompt."
    )


if __name__ == "__main__":
    main()