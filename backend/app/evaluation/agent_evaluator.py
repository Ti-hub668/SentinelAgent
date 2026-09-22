import json
from collections import defaultdict
from pathlib import Path

from app.agent.decision_agent import make_security_decision
from app.schemas.agent_decision import AgentDecisionInput


DATASET_PATH = Path("evals/agent/decision_cases_v1.json")


def load_dataset() -> list[dict]:
    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def run_evaluation() -> None:
    cases = load_dataset()

    total = len(cases)

    action_correct = 0
    priority_correct = 0
    human_review_correct = 0
    fully_correct = 0

    category_stats = defaultdict(
        lambda: {
            "total": 0,
            "correct": 0,
        }
    )

    failures = []

    for case in cases:
        case_id = case["id"]
        category = case["category"]
        description = case["description"]

        input_data = AgentDecisionInput(
            **case["input"]
        )

        expected = case["expected"]

        result = make_security_decision(
            input_data
        )

        action_ok = (
            result.action
            == expected["action"]
        )

        priority_ok = (
            result.priority
            == expected["priority"]
        )

        human_review_ok = (
            result.requires_human_review
            == expected["requires_human_review"]
        )

        case_correct = (
            action_ok
            and priority_ok
            and human_review_ok
        )

        if action_ok:
            action_correct += 1

        if priority_ok:
            priority_correct += 1

        if human_review_ok:
            human_review_correct += 1

        if case_correct:
            fully_correct += 1

        category_stats[category]["total"] += 1

        if case_correct:
            category_stats[category]["correct"] += 1
        else:
            failures.append(
                {
                    "id": case_id,
                    "category": category,
                    "description": description,
                    "input": case["input"],
                    "expected": expected,
                    "actual": {
                        "action": result.action,
                        "priority": result.priority,
                        "requires_human_review": (
                            result.requires_human_review
                        ),
                    },
                }
            )

    print()
    print("=" * 60)
    print("SentinelAgent Decision Agent Evaluation")
    print("=" * 60)

    print(f"Cases: {total}")
    print()

    print(
        "Action Accuracy:       "
        f" {action_correct}/{total}"
        f" ({action_correct / total:.1%})"
    )

    print(
        "Priority Accuracy:     "
        f" {priority_correct}/{total}"
        f" ({priority_correct / total:.1%})"
    )

    print(
        "Human Review Accuracy:"
        f" {human_review_correct}/{total}"
        f" ({human_review_correct / total:.1%})"
    )

    print(
        "Full Policy Accuracy:  "
        f" {fully_correct}/{total}"
        f" ({fully_correct / total:.1%})"
    )

    print()
    print("Category Results")
    print("-" * 60)

    for category, stats in sorted(
        category_stats.items()
    ):
        correct = stats["correct"]
        category_total = stats["total"]

        print(
            f"{category:22}"
            f"{correct}/{category_total}"
            f" ({correct / category_total:.1%})"
        )

    print()
    print("Failed Cases")
    print("-" * 60)

    if not failures:
        print("None")
    else:
        for failure in failures:
            print()
            print(
                f"[{failure['id']}] "
                f"{failure['description']}"
            )

            print(
                f"Category : "
                f"{failure['category']}"
            )

            print(
                f"Expected : "
                f"{failure['expected']}"
            )

            print(
                f"Actual   : "
                f"{failure['actual']}"
            )

    print()
    print("=" * 60)


if __name__ == "__main__":
    run_evaluation()