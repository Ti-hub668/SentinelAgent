import json
from pathlib import Path

from app.ai.two_stage_analyzer import analyze_finding_two_stage
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


def build_finding(
    case: dict,
) -> Finding:
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


def main() -> None:
    cases = load_cases()

    enricher = StructuredIntelligenceEnricher()

    stage1_passed = 0
    final_passed = 0
    full_passed = 0
    errors = 0

    print("=" * 72)
    print("SentinelAgent Two-Stage Analysis Evaluation")
    print("=" * 72)
    print(f"Cases : {len(cases)}")
    print("=" * 72)

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

        expected = case["expected_verdict"]

        try:
            (
                evidence_result,
                enrichment_result,
            ) = analyze_finding_two_stage(
                analysis_input,
                structured_intelligence=(
                    structured_context
                ),
                rag_context=None,
            )

            stage1_ok = (
                evidence_result.preliminary_verdict
                == expected
            )

            final_ok = (
                enrichment_result.final_verdict
                == expected
            )

            full_ok = (
                stage1_ok
                and final_ok
            )

            if stage1_ok:
                stage1_passed += 1

            if final_ok:
                final_passed += 1

            if full_ok:
                full_passed += 1

            status = (
                "PASS"
                if full_ok
                else "FAIL"
            )

            print()
            print(
                f"[{status}] "
                f"{case['id']}"
            )

            print(
                "Finding Category :",
                evidence_result.finding_category,
            )

            print(
                "Evidence Status  :",
                evidence_result.evidence_status,
            )

            print(
                "Stage 1 Verdict  :",
                evidence_result.preliminary_verdict,
            )

            print(
                "Final Verdict    :",
                enrichment_result.final_verdict,
            )

            print(
                "Expected Verdict :",
                expected,
            )

            print(
                "Priority         :",
                enrichment_result.priority,
            )

            print(
                "Stage 1 Match    :",
                stage1_ok,
            )

            print(
                "Final Match      :",
                final_ok,
            )

            print(
                "KEV Match        :",
                intelligence["cisa_kev"]["matched"],
            )

            print(
                "NVD Match        :",
                intelligence["nvd"]["matched"],
            )

        except Exception as exc:
            errors += 1

            print()
            print(
                f"[ERROR] "
                f"{case['id']}"
            )

            print(
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    total = len(cases)
    completed = total - errors


    def completed_pct(
        value: int,
    ) -> float:
        if completed == 0:
            return 0.0

        return value / completed * 100


    def total_pct(
        value: int,
    ) -> float:
        if total == 0:
            return 0.0

        return value / total * 100

    print()
    print("=" * 72)
    print("Two-Stage Evaluation Summary")
    print("=" * 72)

    print(
        f"Total Cases              : "
        f"{total}"
    )

    print(
        f"Completed Cases          : "
        f"{completed}"
    )

    print(
        f"Errors                   : "
        f"{errors}"
    )

    print()

    print(
        "Stage 1 Verdict Accuracy : "
        f"{stage1_passed}/{completed} "
        f"({completed_pct(stage1_passed):.1f}%)"
    )

    print(
        "Final Verdict Accuracy   : "
        f"{final_passed}/{completed} "
        f"({completed_pct(final_passed):.1f}%)"
    )

    print(
        "Full Pipeline Accuracy   : "
        f"{full_passed}/{completed} "
        f"({completed_pct(full_passed):.1f}%)"
    )

    print(
        "Pipeline Completion Rate : "
        f"{completed}/{total} "
        f"({total_pct(completed):.1f}%)"
    )

    print("=" * 72)

if __name__ == "__main__":
    main()