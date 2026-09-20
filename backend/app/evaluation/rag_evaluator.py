import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from statistics import mean

from app.ai.prompt_builder import PROMPT_VERSION
from app.ai.risk_analyst import analyze_finding
from app.core.config import settings
from app.evaluation.prompt_evaluator import (
    build_analysis_input,
    check_ollama_model,
    get_model_name,
    load_eval_cases,
    make_safe_filename,
)
from app.rag.context_builder import build_rag_context
from app.rag.query_builder import build_finding_query
from app.rag.retriever import SecurityKnowledgeRetriever


RESULTS_DIR = Path("evals/results")


def run_rag_evaluation(
    dataset_name: str,
    top_k: int = 3,
) -> None:
    """
    对同一数据集执行 No-RAG 与 RAG 对照评测。
    """

    cases = load_eval_cases(dataset_name)

    total_cases = len(cases)

    retriever = SecurityKnowledgeRetriever()

    no_rag_correct = 0
    rag_correct = 0

    no_rag_successful = 0
    rag_successful = 0

    no_rag_latencies: list[float] = []
    rag_latencies: list[float] = []

    no_rag_confidences: list[float] = []
    rag_confidences: list[float] = []

    improved_cases = 0
    regressed_cases = 0
    unchanged_cases = 0

    case_results: list[dict] = []

    print("=" * 70)
    print("SentinelAgent RAG Evaluation")
    print("=" * 70)

    print(f"Dataset: {dataset_name}")
    print(f"Provider: {settings.LLM_PROVIDER}")
    print(f"Model: {get_model_name()}")
    print(f"Prompt Version: {PROMPT_VERSION}")
    print(f"Top-K: {top_k}")
    print(f"Total Cases: {total_cases}")

    print("=" * 70)

    for index, case in enumerate(
        cases,
        start=1,
    ):
        print()
        print(f"[{index}/{total_cases}] {case.id}")
        print(f"Title: {case.title}")
        print(
            f"Expected Verdict: "
            f"{case.expected_verdict}"
        )

        analysis_input = build_analysis_input(
            case,
            index,
        )

        query = build_finding_query(
            analysis_input
        )

        retrieval_results = retriever.retrieve(
            query=query,
            top_k=top_k,
        )

        rag_context = build_rag_context(
            retrieval_results
        )

        retrieval_data = [
            {
                "rank": rank,
                "document_id": result.document.id,
                "title": result.document.title,
                "category": result.document.category,
                "score": round(result.score, 4),
            }
            for rank, result in enumerate(
                retrieval_results,
                start=1,
            )
        ]

        print("Retrieved:")

        for item in retrieval_data:
            print(
                f"  #{item['rank']} "
                f"{item['score']:.4f} - "
                f"{item['title']}"
            )

        no_rag_result = None
        rag_result = None

        no_rag_error = None
        rag_error = None

        # ------------------------------
        # No-RAG
        # ------------------------------

        start_time = time.perf_counter()

        try:
            no_rag_result = analyze_finding(
                analysis_input
            )

            no_rag_elapsed = (
                time.perf_counter()
                - start_time
            )

            no_rag_successful += 1
            no_rag_latencies.append(
                no_rag_elapsed
            )
            no_rag_confidences.append(
                no_rag_result.confidence
            )

        except Exception as exc:
            no_rag_elapsed = (
                time.perf_counter()
                - start_time
            )

            no_rag_error = (
                f"{type(exc).__name__}: {exc}"
            )

        # ------------------------------
        # RAG
        # ------------------------------

        start_time = time.perf_counter()

        try:
            rag_result = analyze_finding(
                analysis_input,
                rag_context=rag_context,
            )

            rag_elapsed = (
                time.perf_counter()
                - start_time
            )

            rag_successful += 1
            rag_latencies.append(
                rag_elapsed
            )
            rag_confidences.append(
                rag_result.confidence
            )

        except Exception as exc:
            rag_elapsed = (
                time.perf_counter()
                - start_time
            )

            rag_error = (
                f"{type(exc).__name__}: {exc}"
            )

        expected = case.expected_verdict

        no_rag_is_correct = (
            no_rag_result is not None
            and no_rag_result.verdict == expected
        )

        rag_is_correct = (
            rag_result is not None
            and rag_result.verdict == expected
        )

        if no_rag_is_correct:
            no_rag_correct += 1

        if rag_is_correct:
            rag_correct += 1

        if (
            not no_rag_is_correct
            and rag_is_correct
        ):
            improved_cases += 1
            comparison = "improved"

        elif (
            no_rag_is_correct
            and not rag_is_correct
        ):
            regressed_cases += 1
            comparison = "regressed"

        else:
            unchanged_cases += 1
            comparison = "unchanged"

        print(
            "No-RAG:",
            (
                no_rag_result.verdict
                if no_rag_result
                else "ERROR"
            ),
        )

        print(
            "RAG   :",
            (
                rag_result.verdict
                if rag_result
                else "ERROR"
            ),
        )

        print(
            f"Comparison: {comparison}"
        )

        case_results.append(
            {
                "case_id": case.id,
                "title": case.title,
                "expected_verdict": expected,

                "retrieval": retrieval_data,

                "no_rag": {
                    "actual_verdict": (
                        no_rag_result.verdict
                        if no_rag_result
                        else None
                    ),
                    "confidence": (
                        no_rag_result.confidence
                        if no_rag_result
                        else None
                    ),
                    "correct": no_rag_is_correct,
                    "latency_seconds": round(
                        no_rag_elapsed,
                        2,
                    ),
                    "error": no_rag_error,
                },

                "rag": {
                    "actual_verdict": (
                        rag_result.verdict
                        if rag_result
                        else None
                    ),
                    "confidence": (
                        rag_result.confidence
                        if rag_result
                        else None
                    ),
                    "correct": rag_is_correct,
                    "latency_seconds": round(
                        rag_elapsed,
                        2,
                    ),
                    "error": rag_error,
                },

                "comparison": comparison,
            }
        )

    no_rag_accuracy = (
        no_rag_correct / total_cases * 100
        if total_cases
        else 0
    )

    rag_accuracy = (
        rag_correct / total_cases * 100
        if total_cases
        else 0
    )

    no_rag_schema_success = (
        no_rag_successful / total_cases * 100
        if total_cases
        else 0
    )

    rag_schema_success = (
        rag_successful / total_cases * 100
        if total_cases
        else 0
    )

    summary = {
        "dataset": dataset_name,
        "prompt_version": PROMPT_VERSION,
        "provider": settings.LLM_PROVIDER,
        "model": get_model_name(),
        "top_k": top_k,
        "total_cases": total_cases,

        "no_rag": {
            "successful_cases": no_rag_successful,
            "correct_cases": no_rag_correct,
            "schema_success_rate": round(
                no_rag_schema_success,
                2,
            ),
            "verdict_accuracy": round(
                no_rag_accuracy,
                2,
            ),
            "average_latency_seconds": round(
                mean(no_rag_latencies),
                2,
            ) if no_rag_latencies else 0,
            "average_confidence": round(
                mean(no_rag_confidences),
                2,
            ) if no_rag_confidences else 0,
        },

        "rag": {
            "successful_cases": rag_successful,
            "correct_cases": rag_correct,
            "schema_success_rate": round(
                rag_schema_success,
                2,
            ),
            "verdict_accuracy": round(
                rag_accuracy,
                2,
            ),
            "average_latency_seconds": round(
                mean(rag_latencies),
                2,
            ) if rag_latencies else 0,
            "average_confidence": round(
                mean(rag_confidences),
                2,
            ) if rag_confidences else 0,
        },

        "comparison": {
            "improved_cases": improved_cases,
            "regressed_cases": regressed_cases,
            "unchanged_cases": unchanged_cases,
        },

        "evaluated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
    }

    print()
    print("=" * 70)
    print("RAG Evaluation Summary")
    print("=" * 70)

    print(
        f"No-RAG Accuracy: "
        f"{no_rag_accuracy:.2f}%"
    )

    print(
        f"RAG Accuracy: "
        f"{rag_accuracy:.2f}%"
    )

    print(
        f"No-RAG Schema Success: "
        f"{no_rag_schema_success:.2f}%"
    )

    print(
        f"RAG Schema Success: "
        f"{rag_schema_success:.2f}%"
    )

    print(
        f"Improved Cases: "
        f"{improved_cases}"
    )

    print(
        f"Regressed Cases: "
        f"{regressed_cases}"
    )

    print(
        f"Unchanged Cases: "
        f"{unchanged_cases}"
    )

    print(
        f"No-RAG Avg Latency: "
        f"{summary['no_rag']['average_latency_seconds']:.2f}s"
    )

    print(
        f"RAG Avg Latency: "
        f"{summary['rag']['average_latency_seconds']:.2f}s"
    )

    print(
        f"No-RAG Avg Confidence: "
        f"{summary['no_rag']['average_confidence']:.2f}"
    )

    print(
        f"RAG Avg Confidence: "
        f"{summary['rag']['average_confidence']:.2f}"
    )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    model_name = make_safe_filename(
        get_model_name()
    )

    output_path = RESULTS_DIR / (
        f"rag_eval_{dataset_name}_"
        f"{PROMPT_VERSION}_"
        f"{model_name}_"
        f"{timestamp}.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "summary": summary,
                "cases": case_results,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Result saved to: "
        f"{output_path}"
    )

    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "SentinelAgent No-RAG vs RAG Evaluation"
        )
    )

    parser.add_argument(
        "--dataset",
        choices=[
            "development",
            "holdout",
            "real",
            "benchmark_v1",
        ],
        default="real",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
    )

    args = parser.parse_args()

    if args.top_k <= 0:
        raise ValueError(
            "--top-k must be greater than 0"
        )

    if args.model is not None:
        if settings.LLM_PROVIDER.lower() != "ollama":
            raise ValueError(
                "--model currently supports Ollama only"
            )

        check_ollama_model(
            args.model
        )

        settings.OLLAMA_MODEL = args.model

    run_rag_evaluation(
        dataset_name=args.dataset,
        top_k=args.top_k,
    )