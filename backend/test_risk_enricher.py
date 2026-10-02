from app.ai.risk_enricher import enrich_risk
from app.schemas.risk_enrichment import RiskEnrichmentInput


def run_case(
    name: str,
    evidence_status: str,
    preliminary_verdict: str,
    evidence_reason: str,
    expected_verdict: str,
) -> None:
    structured_intelligence = """
CISA KEV:
- matched: true
- known_exploited: true

NVD:
- matched: true
- severity: high
- cvss_score: 8.8
- cwe_ids:
  - CWE-121
"""

    data = RiskEnrichmentInput(
        finding_id=999999,
        finding_category="vulnerability",
        evidence_status=evidence_status,
        preliminary_verdict=preliminary_verdict,
        evidence_confidence=0.95,
        evidence_reason=evidence_reason,
        severity="high",
        risk_score=85,
        risk_level="high",
        structured_intelligence=structured_intelligence,
        rag_context=None,
    )

    result = enrich_risk(data)

    print("=" * 70)
    print(name)
    print("=" * 70)
    print("Evidence Status :", evidence_status)
    print("Preliminary     :", preliminary_verdict)
    print("Final Verdict   :", result.final_verdict)
    print("Priority        :", result.priority)
    print("Confidence      :", result.confidence)
    print("Summary         :", result.summary)
    print("Risk Explanation:", result.risk_explanation)
    print("Intel Context   :", result.intelligence_context)
    print("Action          :", result.recommended_action)

    assert result.final_verdict == expected_verdict, (
        f"{name}: expected {expected_verdict}, "
        f"got {result.final_verdict}"
    )

    print("[PASS]", name)
    print()


def main() -> None:
    run_case(
        name="stage2_confirmed",
        evidence_status="confirmed",
        preliminary_verdict="likely_true_positive",
        evidence_reason=(
            "The affected product and version matched the "
            "scanner rule and the vulnerability-specific "
            "condition was confirmed."
        ),
        expected_verdict="likely_true_positive",
    )

    run_case(
        name="stage2_contradicted",
        evidence_status="contradicted",
        preliminary_verdict="likely_false_positive",
        evidence_reason=(
            "Manual verification identified a different "
            "unaffected product and the original scanner "
            "match came from a generic response."
        ),
        expected_verdict="likely_false_positive",
    )

    run_case(
        name="stage2_insufficient",
        evidence_status="insufficient",
        preliminary_verdict="needs_review",
        evidence_reason=(
            "The target responded, but the affected product, "
            "version, and vulnerability-specific condition "
            "were not confirmed."
        ),
        expected_verdict="needs_review",
    )

    print("=" * 70)
    print("Stage 2 minimal evaluation passed: 3/3")
    print("=" * 70)


if __name__ == "__main__":
    main()