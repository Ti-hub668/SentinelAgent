import json
from pathlib import Path

from app.ai.prompt_builder import PROMPT_VERSION
from app.ai.risk_analyst import analyze_finding
from app.intelligence.structured_enricher import (
    StructuredIntelligenceEnricher,
)
from app.models.finding import Finding
from app.schemas.ai_analysis import AIAnalysisInput


DATASET_PATH = Path(
    "evals/intelligence/intelligence_cases_v1.json"
)


def load_cases() -> list[dict]:
    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def build_finding(case: dict) -> Finding:
    return Finding(
        id=999999,
        scan_task_id=1,
        asset_id=1,
        source=case["source"],
        finding_type=case["finding_type"],
        title=case["title"],
        severity=case["severity"],
        target=case["target"],
        description=case.get("description"),
        evidence=case.get("evidence"),
        remediation=case.get("remediation"),
        template_id=case.get("template_id"),
        cve_ids=json.dumps(
            case.get("cve_ids", []),
            ensure_ascii=False,
        ),
        cwe_ids=json.dumps(
            case.get("cwe_ids", []),
            ensure_ascii=False,
        ),
        status="open",
        risk_score=case["risk_score"],
        risk_level=case["risk_level"],
        risk_reason=case.get("risk_reason"),
    )


def build_analysis_input(
    finding: Finding,
) -> AIAnalysisInput:
    return AIAnalysisInput(
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


def main():
    cases = load_cases()

    enricher = StructuredIntelligenceEnricher()

    passed = 0
    failed = 0

    print()
    print("=" * 70)
    print("SentinelAgent Structured Intelligence Evaluation")
    print("=" * 70)
    print(f"Prompt Version : {PROMPT_VERSION}")
    print(f"Cases          : {len(cases)}")
    print("=" * 70)

    for case in cases:
        finding = build_finding(case)

        intelligence = enricher.enrich(
            finding
        )

        structured_context = None

        if intelligence["identifiers"]["cve_ids"]:
            structured_context = json.dumps(
                intelligence,
                ensure_ascii=False,
                indent=2,
            )

        analysis_input = build_analysis_input(
            finding
        )

        try:
            result = analyze_finding(
                analysis_input,
                rag_context=None,
                structured_intelligence=(
                    structured_context
                ),
            )

            actual = result.verdict
            expected = case["expected_verdict"]

            is_pass = actual == expected

            if is_pass:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"

            print()
            print(
                f"[{status}] {case['id']}"
            )
            print(
                f"Category : {case.get('category', 'N/A')}"
            )
            print(
                f"Expected : {expected}"
            )
            print(
                f"Actual   : {actual}"
            )
            print(
                f"Confidence: {result.confidence}"
            )
            print(
                "KEV Match : "
                f"{intelligence['cisa_kev']['matched']}"
            )
            print(
                "NVD Match : "
                f"{intelligence['nvd']['matched']}"
            )
        except Exception as exc:
            failed += 1

            print()
            print(
                f"[ERROR] {case['id']}"
            )
            print(
                f"{type(exc).__name__}: {exc}"
            )

    total = len(cases)

    accuracy = (
        passed / total
        if total
        else 0.0
    )

    print()
    print("=" * 70)
    print("Evaluation Summary")
    print("=" * 70)
    print(f"Passed   : {passed}")
    print(f"Failed   : {failed}")
    print(
        f"Accuracy : {accuracy:.1%}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()