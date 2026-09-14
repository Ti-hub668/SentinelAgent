import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


RESULTS_DIR = Path("evals/results")


def load_result(file_path: Path) -> dict:
    if not file_path.exists():
        raise FileNotFoundError(
            f"评测结果不存在: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def find_latest_result(
    dataset: str,
    model: str
) -> Path:
    """
    找到指定 dataset + model 最新的评测结果。
    """

    candidates = []

    for file_path in RESULTS_DIR.glob(
        "eval_*.json"
    ):
        try:
            data = load_result(file_path)
        except Exception:
            continue

        summary = data.get(
            "summary",
            {}
        )

        if (
            summary.get("dataset") == dataset
            and summary.get("model") == model
        ):
            candidates.append(
                (
                    summary.get(
                        "evaluated_at",
                        ""
                    ),
                    file_path
                )
            )

    if not candidates:
        raise FileNotFoundError(
            f"没有找到 dataset={dataset}, "
            f"model={model} 的评测结果"
        )

    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidates[0][1]


def analyze_result(
    data: dict
) -> None:
    summary = data.get(
        "summary",
        {}
    )

    cases = data.get(
        "cases",
        []
    )

    print()
    print("=" * 68)
    print(
        "SentinelAgent Evaluation Error Analysis"
    )
    print("=" * 68)

    print(
        f"Dataset         : "
        f"{summary.get('dataset')}"
    )

    print(
        f"Prompt Version  : "
        f"{summary.get('prompt_version')}"
    )

    print(
        f"Model           : "
        f"{summary.get('model')}"
    )

    print(
        f"Total Cases     : "
        f"{len(cases)}"
    )

    # --------------------------------
    # Ground Truth 分类统计
    # --------------------------------

    expected_counts = Counter(
        case.get("expected_verdict")
        for case in cases
    )

    correct_counts = Counter()

    confusion = defaultdict(
        Counter
    )

    errors = []

    for case in cases:
        expected = case.get(
            "expected_verdict"
        )

        actual = case.get(
            "actual_verdict"
        )

        confusion[
            expected
        ][actual] += 1

        if case.get("correct"):
            correct_counts[
                expected
            ] += 1
        else:
            errors.append(
                case
            )

    verdict_order = [
        "informational",
        "likely_true_positive",
        "likely_false_positive",
        "needs_review",
    ]

    print()
    print("Per-Class Accuracy")
    print("-" * 68)

    for verdict in verdict_order:
        total = expected_counts.get(
            verdict,
            0
        )

        correct = correct_counts.get(
            verdict,
            0
        )

        accuracy = (
            correct / total * 100
            if total
            else 0
        )

        print(
            f"{verdict:<28}"
            f"{correct:>3}/{total:<3}"
            f"{accuracy:>8.2f}%"
        )

    # --------------------------------
    # Confusion Matrix
    # --------------------------------

    print()
    print("Confusion Summary")
    print("-" * 68)

    for expected in verdict_order:
        actual_counts = confusion.get(
            expected,
            {}
        )

        if not actual_counts:
            continue

        for actual, count in (
            actual_counts.items()
        ):
            print(
                f"{expected:<28}"
                f" -> "
                f"{actual:<28}"
                f"{count}"
            )

    # --------------------------------
    # 错误案例
    # --------------------------------

    print()
    print("Error Cases")
    print("-" * 68)

    if not errors:
        print(
            "No verdict errors found."
        )
    else:
        for case in errors:
            print()
            print(
                f"Case       : "
                f"{case.get('case_id')}"
            )

            print(
                f"Title      : "
                f"{case.get('title')}"
            )

            print(
                f"Expected   : "
                f"{case.get('expected_verdict')}"
            )

            print(
                f"Actual     : "
                f"{case.get('actual_verdict')}"
            )

            print(
                f"Confidence : "
                f"{case.get('confidence')}"
            )

    # --------------------------------
    # 高置信度错误
    # --------------------------------

    high_confidence_errors = [
        case
        for case in errors
        if (
            case.get("confidence")
            is not None
            and case.get(
                "confidence"
            ) >= 0.9
        )
    ]

    print()
    print("High-Confidence Errors")
    print("-" * 68)

    if not high_confidence_errors:
        print(
            "No high-confidence errors."
        )
    else:
        for case in (
            high_confidence_errors
        ):
            print(
                f"{case.get('case_id')} | "
                f"{case.get('expected_verdict')} "
                f"-> "
                f"{case.get('actual_verdict')} | "
                f"confidence="
                f"{case.get('confidence')}"
            )

    print()
    print("=" * 68)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "SentinelAgent Evaluation "
            "Error Analyzer"
        )
    )

    parser.add_argument(
        "--dataset",
        required=True,
        help=(
            "例如 benchmark_v1 "
            "或 holdout"
        ),
    )

    parser.add_argument(
        "--model",
        default="qwen3:8b",
        help="需要分析的模型",
    )

    args = parser.parse_args()

    result_path = find_latest_result(
        dataset=args.dataset,
        model=args.model
    )

    print(
        f"Using result: {result_path}"
    )

    data = load_result(
        result_path
    )

    analyze_result(
        data
    )


if __name__ == "__main__":
    main()