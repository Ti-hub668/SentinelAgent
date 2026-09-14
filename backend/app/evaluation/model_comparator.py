import json
from pathlib import Path
from datetime import datetime


RESULTS_DIR = Path("evals/results")

TARGET_DATASET = "holdout"
TARGET_PROMPT_VERSION = "v2"


def load_evaluation_results() -> list[dict]:
    """
    读取 evals/results 下的评测结果，
    只保留指定 dataset 和 prompt version。
    """

    results = []

    for file_path in RESULTS_DIR.glob("eval_*.json"):
        try:
            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:
                data = json.load(file)

        except (
            json.JSONDecodeError,
            OSError
        ):
            continue

        summary = data.get(
            "summary",
            {}
        )

        if (
            summary.get("dataset")
            != TARGET_DATASET
        ):
            continue

        if (
            summary.get("prompt_version")
            != TARGET_PROMPT_VERSION
        ):
            continue

        data["_file_path"] = str(
            file_path
        )

        results.append(data)

    return results


def get_latest_result_per_model(
    results: list[dict]
) -> dict[str, dict]:
    """
    每个模型只保留最新一次评测结果。
    """

    latest_results = {}

    for result in results:
        summary = result["summary"]

        model = summary["model"]

        evaluated_at = datetime.fromisoformat(
            summary["evaluated_at"]
        )

        if model not in latest_results:
            latest_results[model] = result
            continue

        old_time = datetime.fromisoformat(
            latest_results[model][
                "summary"
            ]["evaluated_at"]
        )

        if evaluated_at > old_time:
            latest_results[model] = result

    return latest_results


def get_error_cases(
    result: dict
) -> list[dict]:
    """
    获取判断错误的案例。
    """

    return [
        case
        for case in result.get(
            "cases",
            []
        )
        if not case.get(
            "correct",
            False
        )
    ]


def get_high_confidence_errors(
    result: dict,
    threshold: float = 0.9
) -> list[dict]:
    """
    获取高置信度错误。
    """

    errors = get_error_cases(
        result
    )

    return [
        case
        for case in errors
        if (
            case.get("confidence") or 0
        ) >= threshold
    ]


def print_comparison(
    model_results: dict[str, dict]
) -> None:
    """
    在终端打印模型 Benchmark。
    """

    print()
    print("=" * 78)
    print(
        "SentinelAgent Model Benchmark"
    )
    print("=" * 78)

    print(
        f"Dataset: "
        f"{TARGET_DATASET}"
    )

    print(
        f"Prompt Version: "
        f"{TARGET_PROMPT_VERSION}"
    )

    print()

    header = (
        f"{'Model':<20}"
        f"{'Accuracy':>12}"
        f"{'Schema':>12}"
        f"{'Latency':>12}"
        f"{'Confidence':>14}"
        f"{'Errors':>8}"
    )

    print(header)
    print("-" * 78)

    for model, result in model_results.items():
        summary = result["summary"]

        errors = get_error_cases(
            result
        )

        print(
            f"{model:<20}"
            f"{summary['verdict_accuracy']:>11.2f}%"
            f"{summary['schema_success_rate']:>11.2f}%"
            f"{summary['average_latency_seconds']:>11.2f}s"
            f"{summary['average_confidence']:>14.2f}"
            f"{len(errors):>8}"
        )

    print()

    if not model_results:
        return

    best_accuracy_model = max(
        model_results.items(),
        key=lambda item: (
            item[1]["summary"][
                "verdict_accuracy"
            ]
        )
    )[0]

    fastest_model = min(
        model_results.items(),
        key=lambda item: (
            item[1]["summary"][
                "average_latency_seconds"
            ]
        )
    )[0]

    print(
        f"Best Accuracy Model : "
        f"{best_accuracy_model}"
    )

    print(
        f"Fastest Model       : "
        f"{fastest_model}"
    )

    print()
    print("Error Cases")
    print("-" * 78)

    for model, result in model_results.items():
        print()
        print(model)

        errors = get_error_cases(
            result
        )

        if not errors:
            print("  None")
            continue

        for case in errors:
            print(
                "  - "
                f"{case['case_id']} | "
                f"expected="
                f"{case['expected_verdict']} | "
                f"actual="
                f"{case['actual_verdict']} | "
                f"confidence="
                f"{case['confidence']}"
            )

    print()
    print("=" * 78)


def save_comparison(
    model_results: dict[str, dict]
) -> Path:
    """
    保存模型比较结果。
    """

    models = []

    for model, result in model_results.items():
        summary = result["summary"]

        error_cases = get_error_cases(
            result
        )

        high_confidence_errors = (
            get_high_confidence_errors(
                result
            )
        )

        models.append(
            {
                "model": model,
                "verdict_accuracy": (
                    summary[
                        "verdict_accuracy"
                    ]
                ),
                "schema_success_rate": (
                    summary[
                        "schema_success_rate"
                    ]
                ),
                "average_latency_seconds": (
                    summary[
                        "average_latency_seconds"
                    ]
                ),
                "average_confidence": (
                    summary[
                        "average_confidence"
                    ]
                ),
                "error_count": len(
                    error_cases
                ),
                "high_confidence_error_count": (
                    len(
                        high_confidence_errors
                    )
                ),
                "error_cases": [
                    {
                        "case_id": case[
                            "case_id"
                        ],
                        "expected_verdict": case[
                            "expected_verdict"
                        ],
                        "actual_verdict": case[
                            "actual_verdict"
                        ],
                        "confidence": case[
                            "confidence"
                        ]
                    }
                    for case in error_cases
                ]
            }
        )

    comparison = {
        "dataset": TARGET_DATASET,
        "prompt_version": (
            TARGET_PROMPT_VERSION
        ),
        "models": models
    }

    output_path = (
        RESULTS_DIR
        / (
            "model_comparison_"
            f"{TARGET_PROMPT_VERSION}_"
            f"{TARGET_DATASET}.json"
        )
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            comparison,
            file,
            ensure_ascii=False,
            indent=2
        )

    return output_path


def main() -> None:
    results = load_evaluation_results()

    if not results:
        print(
            "没有找到符合条件的评测结果。"
        )
        return

    model_results = (
        get_latest_result_per_model(
            results
        )
    )

    print_comparison(
        model_results
    )

    output_path = save_comparison(
        model_results
    )

    print(
        f"\nComparison saved to: "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()