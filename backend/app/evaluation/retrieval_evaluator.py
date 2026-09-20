import json
from pathlib import Path
from statistics import mean

from app.rag.retriever import SecurityKnowledgeRetriever


EVAL_FILE = Path(
    "evals/retrieval_eval_cases.json"
)


def load_retrieval_cases() -> list[dict]:
    """
    加载 Retrieval Evaluation 数据集。
    """

    with EVAL_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def run_retrieval_evaluation(
    top_k: int = 3,
) -> None:
    """
    评估 RAG Retriever 的检索效果。

    指标：
    - Top-1 Accuracy
    - Hit@K
    - MRR
    """

    cases = load_retrieval_cases()

    retriever = SecurityKnowledgeRetriever()

    total_cases = len(cases)

    top1_correct = 0
    hit_at_k = 0

    reciprocal_ranks = []

    print("=" * 60)
    print("SentinelAgent Retrieval Evaluation")
    print("=" * 60)

    print(f"Cases: {total_cases}")
    print(f"Top-K: {top_k}")

    print("=" * 60)

    for index, case in enumerate(
        cases,
        start=1,
    ):
        query = case["query"]

        expected_document_id = (
            case["expected_document_id"]
        )

        results = retriever.retrieve(
            query=query,
            top_k=top_k,
        )

        retrieved_ids = [
            result.document.metadata.get(
                "parent_id",
                result.document.id,
            )
            for result in results
        ]

        print()
        print(
            f"[{index}/{total_cases}] "
            f"{case['id']}"
        )

        print(
            f"Expected: "
            f"{expected_document_id}"
        )

        expected_rank = None

        for rank, result in enumerate(
            results,
            start=1,
        ):
            document_id = (
                result.document.metadata.get(
                    "parent_id",
                    result.document.id,
                )
            )

            print(
                f"  #{rank} "
                f"{result.score:.4f} - "
                f"{document_id} - "
                f"{result.document.title}"
            )

            if (
                document_id
                == expected_document_id
                and expected_rank is None
            ):
                expected_rank = rank

        # Top-1 Accuracy
        if (
            retrieved_ids
            and retrieved_ids[0]
            == expected_document_id
        ):
            top1_correct += 1

        # Hit@K
        if expected_rank is not None:
            hit_at_k += 1

            reciprocal_rank = (
                1.0 / expected_rank
            )

        else:
            reciprocal_rank = 0.0

        reciprocal_ranks.append(
            reciprocal_rank
        )

        print(
            "Expected Rank:",
            (
                expected_rank
                if expected_rank is not None
                else "Not Found"
            ),
        )

    top1_accuracy = (
        top1_correct / total_cases
        if total_cases
        else 0
    )

    hit_rate = (
        hit_at_k / total_cases
        if total_cases
        else 0
    )

    mrr = (
        mean(reciprocal_ranks)
        if reciprocal_ranks
        else 0
    )

    print()
    print("=" * 60)
    print("Retrieval Evaluation Summary")
    print("=" * 60)

    print(
        f"Total Cases: "
        f"{total_cases}"
    )

    print(
        f"Top-1 Correct: "
        f"{top1_correct}/{total_cases}"
    )

    print(
        f"Top-1 Accuracy: "
        f"{top1_accuracy * 100:.2f}%"
    )

    print(
        f"Hit@{top_k}: "
        f"{hit_rate * 100:.2f}%"
    )

    print(
        f"MRR: "
        f"{mrr:.4f}"
    )

    print("=" * 60)


if __name__ == "__main__":
    run_retrieval_evaluation(
        top_k=3,
    )