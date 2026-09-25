import json
from pathlib import Path

from app.ai.evidence_assessor import assess_evidence
from app.ai.evidence_prompt_builder import EVIDENCE_PROMPT_VERSION
from app.schemas.ai_analysis import AIAnalysisInput


DATASET_PATH = Path(
    "evals/evidence/evidence_cases_v1.json"
)


def load_cases() -> list[dict]:
    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def build_analysis_input(
    case: dict,
) -> AIAnalysisInput:
    return AIAnalysisInput(
        finding_id=999999,
        source=case["source"],
        finding_type=case["finding_type"],
        title=case["title"],
        severity=case["severity"],
        target=case["target"],
        description=case.get("description"),
        evidence=case.get("evidence"),
        remediation=case.get("remediation"),
        risk_score=case["risk_score"],
        risk_level=case["risk_level"],
        risk_reason=case.get("risk_reason"),
    )


def main() -> None:
    cases = load_cases()

    category_passed = 0
    evidence_status_passed = 0
    verdict_passed = 0
    full_passed = 0
    errors = 0

    print("=" * 70)
    print("SentinelAgent Evidence Assessment Evaluation")
    print("=" * 70)
    print(
        f"Evidence Prompt Version : "
        f"{EVIDENCE_PROMPT_VERSION}"
    )
    print(f"Cases                   : {len(cases)}")
    print("=" * 70)

    for case in cases:
        case_id = case["id"]

        expected_category = (
            case["expected_finding_category"]
        )
        expected_status = (
            case["expected_evidence_status"]
        )
        expected_verdict = (
            case["expected_verdict"]
        )

        analysis_input = build_analysis_input(case)

        try:
            result = assess_evidence(
                analysis_input
            )

            category_ok = (
                result.finding_category
                == expected_category
            )

            status_ok = (
                result.evidence_status
                == expected_status
            )

            verdict_ok = (
                result.preliminary_verdict
                == expected_verdict
            )

            full_ok = (
                category_ok
                and status_ok
                and verdict_ok
            )

            if category_ok:
                category_passed += 1

            if status_ok:
                evidence_status_passed += 1

            if verdict_ok:
                verdict_passed += 1

            if full_ok:
                full_passed += 1

            status = (
                "PASS"
                if full_ok
                else "FAIL"
            )

            print()
            print(f"[{status}] {case_id}")
            print(
                f"Dataset Category : "
                f"{case['category']}"
            )

            print(
                f"Finding Category : "
                f"{result.finding_category}"
            )
            print(
                f"Expected Category: "
                f"{expected_category}"
            )
            print(
                f"Category Match   : "
                f"{category_ok}"
            )

            print(
                f"Evidence Status  : "
                f"{result.evidence_status}"
            )
            print(
                f"Expected Status  : "
                f"{expected_status}"
            )
            print(
                f"Status Match     : "
                f"{status_ok}"
            )

            print(
                f"Actual Verdict   : "
                f"{result.preliminary_verdict}"
            )
            print(
                f"Expected Verdict : "
                f"{expected_verdict}"
            )
            print(
                f"Verdict Match    : "
                f"{verdict_ok}"
            )

            print(
                f"Confidence       : "
                f"{result.confidence}"
            )

            print(
                f"Reason           : "
                f"{result.reason}"
            )

        except Exception as exc:
            errors += 1

            print()
            print(f"[ERROR] {case_id}")
            print(
                f"{type(exc).__name__}: {exc}"
            )

    total = len(cases)

    def pct(value: int) -> float:
        if total == 0:
            return 0.0

        return value / total * 100

    print()
    print("=" * 70)
    print("Evidence Assessment Summary")
    print("=" * 70)

    print(
        f"Finding Category Accuracy : "
        f"{category_passed}/{total} "
        f"({pct(category_passed):.1f}%)"
    )

    print(
        f"Evidence Status Accuracy  : "
        f"{evidence_status_passed}/{total} "
        f"({pct(evidence_status_passed):.1f}%)"
    )

    print(
        f"Verdict Accuracy          : "
        f"{verdict_passed}/{total} "
        f"({pct(verdict_passed):.1f}%)"
    )

    print(
        f"Full Assessment Accuracy  : "
        f"{full_passed}/{total} "
        f"({pct(full_passed):.1f}%)"
    )

    print(
        f"Errors                    : "
        f"{errors}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()