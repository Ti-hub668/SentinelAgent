import json

from app.models.finding import Finding
from app.schemas.ai_analysis import AIAnalysisInput
from app.intelligence.structured_enricher import (
    StructuredIntelligenceEnricher,
)
from app.ai.risk_analyst import analyze_finding


def main():
    # 这是合成测试。
    # CVE 是真实 KEV 标识符，但 Evidence 故意设计为不足。
    finding = Finding(
        id=999999,
        scan_task_id=1,
        asset_id=1,
        source="nuclei",
        finding_type="vulnerability",
        title="Possible CVE-2026-7273",
        severity="high",
        target="127.0.0.1",
        description=(
            "Scanner reports a possible match "
            "for CVE-2026-7273."
        ),
        evidence=(
            "Target responded to a network request, "
            "but no affected product version or "
            "vulnerability condition was confirmed."
        ),
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
        risk_reason=(
            "Synthetic high-risk test case."
        ),
    )

    enricher = StructuredIntelligenceEnricher()

    intelligence_result = enricher.enrich(
        finding
    )

    assert intelligence_result[
        "cisa_kev"
    ]["matched"] is True

    structured_context = json.dumps(
        intelligence_result,
        ensure_ascii=False,
        indent=2,
    )

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

    result = analyze_finding(
        analysis_input,
        rag_context=None,
        structured_intelligence=structured_context,
    )

    print()
    print("=" * 60)
    print("Evidence vs KEV Boundary Test")
    print("=" * 60)

    print("Verdict:")
    print(result.verdict)

    print()

    print("Confidence:")
    print(result.confidence)

    print()

    print("Summary:")
    print(result.summary)

    print()

    print("Risk Explanation:")
    print(result.risk_explanation)

    print()

    print("Recommended Action:")
    print(result.recommended_action)

    print()
    print("=" * 60)

    if result.verdict == "likely_true_positive":
        print(
            "WARNING: Model may be treating KEV "
            "intelligence as direct Finding evidence."
        )
    else:
        print(
            "PASS: Model did not automatically convert "
            "KEV intelligence into direct evidence."
        )


if __name__ == "__main__":
    main()