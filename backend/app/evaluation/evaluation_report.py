import json
from pathlib import Path


RESULTS_DIR = Path("evals/results")

REPORT_RESULTS = {
    "holdout": (
        "eval_holdout_v2_qwen3_8b_20260914_150146.json"
    ),
    "benchmark_v1": (
        "eval_benchmark_v1_v2_qwen3_8b_20260914_174027.json"
    ),
    "real": (
        "eval_real_v2_qwen3_8b_20260919_153616.json"
    ),
}


def load_result(filename: str) -> dict:
    """
    加载单个评测结果文件。
    """

    path = RESULTS_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Evaluation result not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def print_dataset_report(
    dataset_name: str,
    result: dict
) -> None:
    """
    输出单个数据集的核心评测指标。
    """

    summary = result["summary"]

    print()
    print("-" * 60)
    print(f"Dataset: {dataset_name}")
    print("-" * 60)

    print(
        f"Prompt Version      : "
        f"{summary['prompt_version']}"
    )

    print(
        f"Model               : "
        f"{summary['model']}"
    )

    print(
        f"Total Cases         : "
        f"{summary['total_cases']}"
    )

    print(
        f"Successful Cases    : "
        f"{summary['successful_cases']}"
    )

    print(
        f"Correct Cases       : "
        f"{summary['correct_cases']}"
    )

    print(
        f"Schema Success Rate : "
        f"{summary['schema_success_rate']:.2f}%"
    )

    print(
        f"Verdict Accuracy    : "
        f"{summary['verdict_accuracy']:.2f}%"
    )

    print(
        f"Average Confidence  : "
        f"{summary['average_confidence']:.2f}"
    )

    print(
        f"Average Latency     : "
        f"{summary['average_latency_seconds']:.2f}s"
    )

VERDICTS = [
    "informational",
    "likely_true_positive",
    "likely_false_positive",
    "needs_review",
]


def print_verdict_performance(
    dataset_name: str,
    result: dict
) -> None:
    """
    按 verdict 类型统计评测表现。
    """

    cases = result["cases"]

    print()
    print("-" * 60)
    print(f"Verdict Performance: {dataset_name}")
    print("-" * 60)

    print(
        f"{'Verdict':<28}"
        f"{'Cases':>8}"
        f"{'Correct':>10}"
        f"{'Accuracy':>12}"
    )

    print("-" * 58)

    for verdict in VERDICTS:
        verdict_cases = [
            case
            for case in cases
            if case["expected_verdict"] == verdict
        ]

        total = len(verdict_cases)

        correct = sum(
            1
            for case in verdict_cases
            if case["correct"]
        )

        accuracy = (
            correct / total * 100
            if total
            else 0
        )

        print(
            f"{verdict:<28}"
            f"{total:>8}"
            f"{correct:>10}"
            f"{accuracy:>11.2f}%"
        )


def print_error_analysis(
    dataset_name: str,
    result: dict
) -> None:
    """
    输出模型判断错误的样本。
    """

    error_cases = [
        case
        for case in result["cases"]
        if not case["correct"]
    ]

    print()
    print("-" * 60)
    print(f"Error Analysis: {dataset_name}")
    print("-" * 60)

    if not error_cases:
        print("No verdict errors found.")
        return

    for case in error_cases:
        print()
        print(f"Case ID    : {case['case_id']}")
        print(f"Title      : {case['title']}")

        print(
            f"Expected   : "
            f"{case['expected_verdict']}"
        )

        print(
            f"Actual     : "
            f"{case['actual_verdict']}"
        )

        confidence = case["confidence"]

        if confidence is not None:
            print(
                f"Confidence : "
                f"{confidence:.2f}"
            )

        if case["summary"]:
            print(
                f"Summary    : "
                f"{case['summary']}"
            )

        if case["risk_explanation"]:
            print(
                f"Reason     : "
                f"{case['risk_explanation']}"
            )

        if case["error"]:
            print(
                f"Error      : "
                f"{case['error']}"
            )

def main() -> None:
    """
    汇总 SentinelAgent 的核心评测结果。
    """

    print("=" * 60)
    print("SentinelAgent Evaluation Report")
    print("=" * 60)

    loaded_results = {}

    for dataset_name, filename in REPORT_RESULTS.items():
        result = load_result(filename)

        loaded_results[dataset_name] = result

        print_dataset_report(
            dataset_name,
            result
        )
    for dataset_name, result in loaded_results.items():
        print_verdict_performance(
            dataset_name,
            result
        )

        print_error_analysis(
            dataset_name,
            result
        )
    print()
    print("=" * 60)
    print("Evaluation Overview")
    print("=" * 60)

    print(
        f"{'Dataset':<18}"
        f"{'Cases':>8}"
        f"{'Accuracy':>12}"
        f"{'Schema':>12}"
        f"{'Confidence':>14}"
        f"{'Latency':>12}"
    )

    print("-" * 76)

    for dataset_name, result in loaded_results.items():
        summary = result["summary"]

        print(
            f"{dataset_name:<18}"
            f"{summary['total_cases']:>8}"
            f"{summary['verdict_accuracy']:>11.2f}%"
            f"{summary['schema_success_rate']:>11.2f}%"
            f"{summary['average_confidence']:>14.2f}"
            f"{summary['average_latency_seconds']:>11.2f}s"
        )

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()