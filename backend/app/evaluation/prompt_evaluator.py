import json
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from statistics import mean

from app.ai.prompt_builder import PROMPT_VERSION
from app.ai.risk_analyst import analyze_finding
from app.core.config import settings
from app.evaluation.eval_schema import EvalCase
from app.schemas.ai_analysis import AIAnalysisInput


RESULTS_DIR = Path("evals/results")


DATASETS = {
    "development": Path(
        "evals/prompt_eval_cases.json"
    ),
    "holdout": Path(
        "evals/prompt_holdout_cases.json"
    ),
    "real": Path(
        "evals/real_findings_labeled_v1.json"
    ),
    "benchmark_v1": Path(
        "evals/security_benchmark_v1.json"
    ),
}


def load_eval_cases(
    dataset_name: str
) -> list[EvalCase]:
    """
    根据数据集名称加载评测样本。
    """

    eval_file = DATASETS[dataset_name]

    with eval_file.open(
        "r",
        encoding="utf-8"
    ) as file:
        raw_cases = json.load(file)

    return [
        EvalCase.model_validate(item)
        for item in raw_cases
    ]


def get_model_name() -> str:
    """
    获取当前正在使用的模型名称。
    """

    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        return settings.OLLAMA_MODEL

    if provider == "openai":
        return settings.OPENAI_MODEL

    return "unknown"
def check_ollama_model(model_name: str) -> None:
    """
    检查指定的 Ollama 模型是否已经安装。
    """

    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=10,
            check=True
        )

    except FileNotFoundError as exc:
        raise RuntimeError(
            "未找到 Ollama，请确认 Ollama 已正确安装。"
        ) from exc

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "检查 Ollama 模型时超时。"
        ) from exc

    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "无法读取 Ollama 模型列表。"
        ) from exc

    installed_models = []

    lines = result.stdout.splitlines()

    for line in lines[1:]:
        parts = line.split()

        if parts:
            installed_models.append(
                parts[0]
            )

    if model_name not in installed_models:
        raise ValueError(
            f"Ollama 模型未安装: {model_name}\n"
            f"当前已安装模型: "
            f"{', '.join(installed_models)}"
        )

def build_analysis_input(
    case: EvalCase,
    index: int
) -> AIAnalysisInput:
    """
    将评测样本转换成 AI 分析输入。
    """

    return AIAnalysisInput(
        finding_id=index,
        source=case.source,
        finding_type=case.finding_type,
        title=case.title,
        severity=case.severity,
        target=case.target,
        description=case.description,
        evidence=case.evidence,
        remediation=case.remediation,
        risk_score=case.risk_score,
        risk_level=case.risk_level,
        risk_reason=case.risk_reason
    )


def make_safe_filename(value: str) -> str:
    """
    将模型名称转换为适合 Windows 文件名的格式。
    """

    return (
        value
        .replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )


def save_evaluation_result(
    summary: dict,
    case_results: list[dict],
    dataset_name: str
) -> Path:
    """
    将评测结果保存为 JSON 文件。
    """

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    model_name = make_safe_filename(
        get_model_name()
    )

    filename = (
        f"eval_{dataset_name}_"
        f"{PROMPT_VERSION}_"
        f"{model_name}_"
        f"{timestamp}.json"
    )

    output_path = RESULTS_DIR / filename

    output_data = {
        "summary": summary,
        "cases": case_results
    }

    with output_path.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    return output_path


def run_evaluation(
    dataset_name: str
):
    """
    执行完整 Prompt Evaluation。
    """

    cases = load_eval_cases(
    dataset_name
    )
    total_cases = len(cases)

    successful_cases = 0
    correct_cases = 0

    latencies = []
    confidences = []

    case_results = []

    print("=" * 60)
    print("SentinelAgent Prompt Evaluation")
    print("=" * 60)

    print(
    f"Dataset: {dataset_name}"
    )
    print(f"Provider: {settings.LLM_PROVIDER}")
    print(f"Model: {get_model_name()}")
    print(f"Prompt Version: {PROMPT_VERSION}")
    print(f"Total Cases: {total_cases}")

    print("=" * 60)

    for index, case in enumerate(
        cases,
        start=1
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
            index
        )

        start_time = time.perf_counter()

        try:
            result = analyze_finding(
                analysis_input
            )

            elapsed = (
                time.perf_counter()
                - start_time
            )

            successful_cases += 1

            latencies.append(elapsed)
            confidences.append(
                result.confidence
            )

            is_correct = (
                result.verdict
                == case.expected_verdict
            )

            if is_correct:
                correct_cases += 1

            case_result = {
                "case_id": case.id,
                "title": case.title,
                "expected_verdict": (
                    case.expected_verdict
                ),
                "actual_verdict": (
                    result.verdict
                ),
                "confidence": (
                    result.confidence
                ),
                "correct": is_correct,
                "latency_seconds": round(
                    elapsed,
                    2
                ),
                "summary": result.summary,
                "risk_explanation": (
                    result.risk_explanation
                ),
                "recommended_action": (
                    result.recommended_action
                ),
                "error": None
            }

            case_results.append(
                case_result
            )

            print(
                f"Actual Verdict: "
                f"{result.verdict}"
            )

            print(
                f"Confidence: "
                f"{result.confidence:.2f}"
            )

            print(
                f"Correct: "
                f"{is_correct}"
            )

            print(
                f"Latency: "
                f"{elapsed:.2f}s"
            )

        except Exception as exc:
            elapsed = (
                time.perf_counter()
                - start_time
            )

            case_results.append(
                {
                    "case_id": case.id,
                    "title": case.title,
                    "expected_verdict": (
                        case.expected_verdict
                    ),
                    "actual_verdict": None,
                    "confidence": None,
                    "correct": False,
                    "latency_seconds": round(
                        elapsed,
                        2
                    ),
                    "summary": None,
                    "risk_explanation": None,
                    "recommended_action": None,
                    "error": (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )
                }
            )

            print("Evaluation failed")

            print(
                f"Error: "
                f"{type(exc).__name__}: {exc}"
            )

            print(
                f"Latency: "
                f"{elapsed:.2f}s"
            )

    schema_success_rate = (
        successful_cases / total_cases * 100
        if total_cases
        else 0
    )

    verdict_accuracy = (
        correct_cases / total_cases * 100
        if total_cases
        else 0
    )

    average_latency = (
        mean(latencies)
        if latencies
        else 0
    )

    average_confidence = (
        mean(confidences)
        if confidences
        else 0
    )

    summary = {
        "dataset": dataset_name,
        "prompt_version": PROMPT_VERSION,
        "provider": settings.LLM_PROVIDER,
        "model": get_model_name(),
        "total_cases": total_cases,
        "successful_cases": successful_cases,
        "correct_cases": correct_cases,
        "schema_success_rate": round(
            schema_success_rate,
            2
        ),
        "verdict_accuracy": round(
            verdict_accuracy,
            2
        ),
        "average_latency_seconds": round(
            average_latency,
            2
        ),
        "average_confidence": round(
            average_confidence,
            2
        ),
        "evaluated_at": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    print()
    print("=" * 60)
    print("Evaluation Summary")
    print("=" * 60)

    print(
        f"Prompt Version: "
        f"{PROMPT_VERSION}"
    )

    print(
        f"Model: "
        f"{get_model_name()}"
    )

    print(
        f"Total Cases: "
        f"{total_cases}"
    )

    print(
        f"Successful Cases: "
        f"{successful_cases}"
    )

    print(
        f"Correct Cases: "
        f"{correct_cases}"
    )

    print(
        f"Schema Success Rate: "
        f"{schema_success_rate:.2f}%"
    )

    print(
        f"Verdict Accuracy: "
        f"{verdict_accuracy:.2f}%"
    )

    print(
        f"Average Latency: "
        f"{average_latency:.2f}s"
    )

    print(
        f"Average Confidence: "
        f"{average_confidence:.2f}"
    )

    output_path = save_evaluation_result(
    summary,
    case_results,
    dataset_name
    )

    print()
    print(
        f"Result saved to: "
        f"{output_path}"
    )

    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "SentinelAgent Prompt Evaluation"
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
    default="development",
    help="选择需要运行的评测数据集"
    )
    
    parser.add_argument(
    "--model",
    type=str,
    default=None,
    help=(
        "临时指定 Ollama 模型，"
        "例如 qwen3:8b 或 qwen3:14b"
    )
    )

    args = parser.parse_args()

    
    if args.model is not None:
        if settings.LLM_PROVIDER.lower() != "ollama":
            raise ValueError(
                "--model 参数目前仅支持 Ollama"
            )

        check_ollama_model(
            args.model
        )

        settings.OLLAMA_MODEL = args.model

        run_evaluation(
            args.dataset
        )