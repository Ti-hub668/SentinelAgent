from app.agent.graph import investigation_graph


INVALID_FINDING_ID = 999999


def main():
    result = investigation_graph.invoke(
        {
            "finding_id": INVALID_FINDING_ID,
            "status": "pending",
        }
    )

    assert (
        result["status"]
        == "failed"
    )

    assert (
        result["failed_node"]
        == "build_context"
    )

    assert result["error"]

    assert (
        "context" not in result
    )

    assert (
        "evidence_assessment"
        not in result
    )

    print(
        "[PASS] invalid finding stopped safely"
    )

    print(
        "Failed node:",
        result["failed_node"],
    )

    print(
        "Error:",
        result["error"],
    )

    print(
        "\nInvestigation Fail-Safe evaluation PASSED"
    )


if __name__ == "__main__":
    main()