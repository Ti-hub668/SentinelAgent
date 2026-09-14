import argparse
import json
from collections import Counter
from pathlib import Path


VALID_VERDICTS = {
    "informational",
    "likely_true_positive",
    "likely_false_positive",
    "needs_review",
}


REQUIRED_FIELDS = {
    "id",
    "source",
    "finding_type",
    "title",
    "severity",
    "target",
    "expected_verdict",
}


DATASETS = {
    "development": Path(
        "evals/prompt_eval_cases.json"
    ),
    "holdout": Path(
        "evals/prompt_holdout_cases.json"
    ),
    "real": Path(
        "evals/real_findings_labeled.json"
    ),
    "benchmark_v1": Path(
        "evals/security_benchmark_v1.json"
    ),
}


def load_dataset(
    file_path: Path
) -> list[dict]:
    """
    加载 JSON 数据集。
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"数据集不存在: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "数据集顶层必须是 JSON 数组"
        )

    return data


def normalize_text(
    value
) -> str:
    """
    对用于重复检测的文本进行简单标准化。
    """

    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


def build_duplicate_key(
    case: dict
) -> tuple:
    """
    根据 Finding 核心字段生成重复检测键。

    finding_id 和 risk_score 等字段不参与，
    因为同一个 Finding 可能在不同扫描运行中
    被重复记录。
    """

    return (
        normalize_text(
            case.get("source")
        ),
        normalize_text(
            case.get("finding_type")
        ),
        normalize_text(
            case.get("title")
        ),
        normalize_text(
            case.get("target")
        ),
        normalize_text(
            case.get("evidence")
        ),
    )


def validate_required_fields(
    cases: list[dict]
) -> list[str]:
    """
    检查必填字段。
    """

    errors = []

    for index, case in enumerate(
        cases,
        start=1
    ):
        missing_fields = (
            REQUIRED_FIELDS
            - set(case.keys())
        )

        if missing_fields:
            errors.append(
                f"第 {index} 条数据 "
                f"缺少字段: "
                f"{sorted(missing_fields)}"
            )

    return errors


def validate_case_ids(
    cases: list[dict]
) -> list[str]:
    """
    检查 case id 是否为空或重复。
    """

    errors = []
    seen_ids = set()

    for index, case in enumerate(
        cases,
        start=1
    ):
        case_id = case.get("id")

        if not case_id:
            errors.append(
                f"第 {index} 条数据 "
                f"id 为空"
            )
            continue

        if case_id in seen_ids:
            errors.append(
                f"发现重复 case id: "
                f"{case_id}"
            )

        seen_ids.add(case_id)

    return errors


def validate_verdicts(
    cases: list[dict]
) -> list[str]:
    """
    检查 expected_verdict。
    """

    errors = []

    for case in cases:
        case_id = case.get(
            "id",
            "<unknown>"
        )

        verdict = case.get(
            "expected_verdict"
        )

        if verdict not in VALID_VERDICTS:
            errors.append(
                f"{case_id}: "
                f"非法 expected_verdict="
                f"{verdict!r}"
            )

    return errors


def find_duplicates(
    cases: list[dict]
) -> list[list[str]]:
    """
    检测核心内容重复的 Finding。
    """

    duplicate_map = {}

    for case in cases:
        key = build_duplicate_key(
            case
        )

        case_id = case.get(
            "id",
            "<unknown>"
        )

        duplicate_map.setdefault(
            key,
            []
        ).append(
            case_id
        )

    duplicates = [
        case_ids
        for case_ids
        in duplicate_map.values()
        if len(case_ids) > 1
    ]

    return duplicates


def count_verdicts(
    cases: list[dict]
) -> Counter:
    """
    统计标签数量。
    """

    return Counter(
        case.get(
            "expected_verdict"
        )
        for case in cases
    )


def validate_optional_content(
    cases: list[dict]
) -> list[str]:
    """
    对缺少关键内容但格式合法的数据给出 Warning。
    """

    warnings = []

    for case in cases:
        case_id = case.get(
            "id",
            "<unknown>"
        )

        title = normalize_text(
            case.get("title")
        )

        evidence = normalize_text(
            case.get("evidence")
        )

        if not title:
            warnings.append(
                f"{case_id}: "
                f"title 为空"
            )

        if not evidence:
            warnings.append(
                f"{case_id}: "
                f"evidence 为空"
            )

    return warnings


def print_distribution(
    cases: list[dict]
) -> None:
    """
    打印四种 verdict 的标签分布。
    """

    counts = count_verdicts(
        cases
    )

    total = len(cases)

    print()
    print("Verdict Distribution")
    print("-" * 60)

    for verdict in [
        "informational",
        "likely_true_positive",
        "likely_false_positive",
        "needs_review",
    ]:
        count = counts.get(
            verdict,
            0
        )

        if total:
            percentage = (
                count / total * 100
            )
        else:
            percentage = 0

        print(
            f"{verdict:<28}"
            f"{count:>5} "
            f"({percentage:>6.2f}%)"
        )


def validate_dataset(
    dataset_name: str
) -> bool:
    """
    执行完整数据集验证。

    返回：
    True  = 没有严重错误
    False = 存在严重错误
    """

    file_path = DATASETS[
        dataset_name
    ]

    cases = load_dataset(
        file_path
    )

    print()
    print("=" * 60)
    print(
        "SentinelAgent Dataset Validator"
    )
    print("=" * 60)

    print(
        f"Dataset : {dataset_name}"
    )

    print(
        f"File    : {file_path}"
    )

    print(
        f"Cases   : {len(cases)}"
    )

    errors = []

    errors.extend(
        validate_required_fields(
            cases
        )
    )

    errors.extend(
        validate_case_ids(
            cases
        )
    )

    errors.extend(
        validate_verdicts(
            cases
        )
    )

    warnings = (
        validate_optional_content(
            cases
        )
    )

    duplicates = find_duplicates(
        cases
    )

    print_distribution(
        cases
    )

    print()
    print("Duplicate Check")
    print("-" * 60)

    if duplicates:
        for duplicate_group in duplicates:
            print(
                "Duplicate group: "
                + ", ".join(
                    duplicate_group
                )
            )
    else:
        print(
            "No duplicate findings found."
        )

    print()
    print("Warnings")
    print("-" * 60)

    if warnings:
        for warning in warnings:
            print(
                f"- {warning}"
            )
    else:
        print(
            "No warnings."
        )

    print()
    print("Errors")
    print("-" * 60)

    if errors:
        for error in errors:
            print(
                f"- {error}"
            )
    else:
        print(
            "No validation errors."
        )

    print()
    print("=" * 60)

    if errors:
        print(
            "Validation Result: FAILED"
        )
        return False

    print(
        "Validation Result: PASSED"
    )

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "SentinelAgent Evaluation "
            "Dataset Validator"
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
        required=True,
        help="选择需要检查的数据集",
    )

    args = parser.parse_args()

    validate_dataset(
        args.dataset
    )


if __name__ == "__main__":
    main()