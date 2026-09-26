import json
import time
import argparse
import httpx
from pathlib import Path

from app.ai.two_stage_analyzer import analyze_finding_two_stage
from app.db.database import SessionLocal
from app.intelligence.structured_enricher import StructuredIntelligenceEnricher
from app.models.finding import Finding
from app.rag.context_builder import build_rag_context
from app.rag.query_builder import build_finding_query
from app.rag.retriever import SecurityKnowledgeRetriever
from app.schemas.ai_analysis import AIAnalysisInput


BASE_DIR = Path(__file__).resolve().parents[2]

GROUND_TRUTH_FILES = {
    "v1": BASE_DIR
    / "evals"
    / "real_findings_ground_truth_v1.json",

    "v2": BASE_DIR
    / "evals"
    / "real_findings_ground_truth_v2.json",
}

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "SentinelAgent Real Ground Truth Evaluation"
        )
    )

    parser.add_argument(
        "--dataset",
        choices=["v1", "v2"],
        default="v1",
        help=(
            "选择真实 Ground Truth 数据集版本，"
            "默认使用 v1"
        ),
    )

    return parser.parse_args()

def load_ground_truth(dataset_version: str):
    path = GROUND_TRUTH_FILES[dataset_version]

    if not path.exists():
        raise FileNotFoundError(
            f"Ground Truth dataset not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        cases = json.load(f)

    return path, cases

def build_analysis_input(
    finding: Finding,
) -> AIAnalysisInput:
    return AIAnalysisInput(
        finding_id=finding.id,
        source=finding.source,
        title=finding.title,
        severity=finding.severity,
        finding_type=finding.finding_type,
        target=finding.target,
        description=finding.description or "",
        evidence=finding.evidence or "",
        remediation=finding.remediation or "",
        risk_score=finding.risk_score,
        risk_level=finding.risk_level,
        risk_reason=finding.risk_reason or "",
    )


def build_rag_for_finding(
    finding: Finding,
) -> str | None:
    query = build_finding_query(finding)

    retriever = SecurityKnowledgeRetriever()

    results = retriever.retrieve(
        query=query,
        top_k=1,
    )

    if not results:
        return None

    return build_rag_context(results)

def run_two_stage_with_retry(
    analysis_input,
    structured_intelligence,
    rag_context,
    max_attempts: int = 3,
):
    """
    对真实 Ground Truth 评测中的临时 LLM 错误进行有限重试。

    仅针对：
    - Ollama / HTTP timeout
    - LLM structured output schema error

    不改变任何模型判断结果。
    """

    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            return analyze_finding_two_stage(
                analysis_input,
                structured_intelligence=structured_intelligence,
                rag_context=rag_context,
            )

        except httpx.ReadTimeout as exc:
            last_error = exc

        except RuntimeError as exc:
            if (
                "does not match EvidenceAssessmentResult schema"
                not in str(exc)
            ):
                raise

            last_error = exc

        if attempt < max_attempts:
            print(
                f"[RETRY] attempt {attempt}/{max_attempts} failed: "
                f"{type(last_error).__name__}: {last_error}"
            )
            time.sleep(1)

    raise last_error

def evaluate() -> None:
    args = parse_args()

    dataset_path, cases = load_ground_truth(
        args.dataset
    )

    db = SessionLocal()

    category_correct = 0
    status_correct = 0
    preliminary_correct = 0
    final_correct = 0
    full_correct = 0
    completed = 0
    errors = 0

    intelligence_enricher = StructuredIntelligenceEnricher()

    print("=" * 72)
    print("SentinelAgent Real Ground Truth Evaluation")
    print("=" * 72)
    print(f"Dataset : {dataset_path}")
    print(f"Version : {args.dataset}")
    print(f"Cases   : {len(cases)}")
    print()

    try:
        for case in cases:
            case_id = case.get("case_id") or case.get("id")
            finding_id = case["finding_id"]

            print("-" * 72)
            print(
                f"[{case_id}] "
                f"Finding {finding_id} - "
                f"{case['title']}"
            )

            finding = (
                db.query(Finding)
                .filter(Finding.id == finding_id)
                .first()
            )

            if finding is None:
                print(
                    f"[ERROR] Finding {finding_id} "
                    "not found in database."
                )
                errors += 1
                continue

            try:
                analysis_input = build_analysis_input(
                    finding
                )

                structured_intelligence = (
                    intelligence_enricher.enrich(
                        finding
                    )
                )

                if not finding.cve_ids:
                    structured_intelligence = None
                else:
                    structured_intelligence = json.dumps(
                        structured_intelligence,
                        ensure_ascii=False,
                    )

                rag_context = build_rag_for_finding(
                    finding
                )

                evidence_result, enrichment_result = (
                    run_two_stage_with_retry(
                        analysis_input,
                        structured_intelligence,
                        rag_context,
                    )
                )

                category_ok = (
                    evidence_result.finding_category
                    == case["expected_category"]
                )

                status_ok = (
                    evidence_result.evidence_status
                    == case[
                        "expected_evidence_status"
                    ]
                )

                preliminary_ok = (
                    evidence_result.preliminary_verdict
                    == case[
                        "expected_preliminary_verdict"
                    ]
                )

                final_ok = (
                    enrichment_result.final_verdict
                    == case[
                        "expected_final_verdict"
                    ]
                )

                case_full_ok = all(
                    [
                        category_ok,
                        status_ok,
                        preliminary_ok,
                        final_ok,
                    ]
                )

                category_correct += int(category_ok)
                status_correct += int(status_ok)
                preliminary_correct += int(
                    preliminary_ok
                )
                final_correct += int(final_ok)
                full_correct += int(case_full_ok)
                completed += 1

                print(
                    "Category:"
                )
                print(
                    "  expected:",
                    case["expected_category"],
                )
                print(
                    "  actual  :",
                    evidence_result.finding_category,
                )
                print(
                    "  result  :",
                    "PASS" if category_ok else "FAIL",
                )

                print(
                    "Evidence Status:"
                )
                print(
                    "  expected:",
                    case[
                        "expected_evidence_status"
                    ],
                )
                print(
                    "  actual  :",
                    evidence_result.evidence_status,
                )
                print(
                    "  result  :",
                    "PASS" if status_ok else "FAIL",
                )

                print(
                    "Preliminary Verdict:"
                )
                print(
                    "  expected:",
                    case[
                        "expected_preliminary_verdict"
                    ],
                )
                print(
                    "  actual  :",
                    evidence_result.preliminary_verdict,
                )
                print(
                    "  result  :",
                    (
                        "PASS"
                        if preliminary_ok
                        else "FAIL"
                    ),
                )

                print(
                    "Final Verdict:"
                )
                print(
                    "  expected:",
                    case[
                        "expected_final_verdict"
                    ],
                )
                print(
                    "  actual  :",
                    enrichment_result.final_verdict,
                )
                print(
                    "  result  :",
                    "PASS" if final_ok else "FAIL",
                )

                print(
                    "Full Pipeline:",
                    "PASS" if case_full_ok else "FAIL",
                )

            except Exception as exc:
                errors += 1
                print(
                    f"[ERROR] {type(exc).__name__}: "
                    f"{exc}"
                )

    finally:
        db.close()

    print()
    print("=" * 72)
    print("Summary")
    print("=" * 72)

    print(f"Total Cases       : {len(cases)}")
    print(f"Completed Cases   : {completed}")
    print(f"Errors            : {errors}")

    if completed > 0:
        print(
            "Category Accuracy  : "
            f"{category_correct}/{completed} "
            f"({category_correct / completed:.1%})"
        )

        print(
            "Evidence Accuracy  : "
            f"{status_correct}/{completed} "
            f"({status_correct / completed:.1%})"
        )

        print(
            "Preliminary Acc.   : "
            f"{preliminary_correct}/{completed} "
            f"({preliminary_correct / completed:.1%})"
        )

        print(
            "Final Accuracy     : "
            f"{final_correct}/{completed} "
            f"({final_correct / completed:.1%})"
        )

        print(
            "Full Pipeline Acc. : "
            f"{full_correct}/{completed} "
            f"({full_correct / completed:.1%})"
        )

    print(
        "Completion Rate    : "
        f"{completed}/{len(cases)} "
        f"({completed / len(cases):.1%})"
    )


if __name__ == "__main__":
    evaluate()