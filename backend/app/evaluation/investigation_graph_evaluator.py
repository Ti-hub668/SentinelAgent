from app.agent.graph import investigation_graph


TEST_FINDING_ID = 62


def main():
    """
    Evaluate the normal SentinelAgent investigation workflow.

    This evaluator verifies:
    1. Context construction
    2. Deterministic triage
    3. Conditional research routing
    4. Evidence assessment
    5. Risk enrichment
    6. Final workflow state
    """

    result = investigation_graph.invoke(
        {
            "finding_id": TEST_FINDING_ID,
            "status": "pending",
        }
    )

    # --------------------------------------------------
    # Context
    # --------------------------------------------------

    assert (
        result["finding_id"]
        == TEST_FINDING_ID
    )

    assert "context" in result

    assert (
        result["context"].finding.id
        == TEST_FINDING_ID
    )

    print(
        "[PASS] context node"
    )

    # --------------------------------------------------
    # Triage
    # --------------------------------------------------

    assert "needs_research" in result

    assert isinstance(
        result["needs_research"],
        bool,
    )

    assert (
        result["triage_reason"].strip()
    )

    print(
        "[PASS] triage node"
    )

    # --------------------------------------------------
    # Conditional Research
    # --------------------------------------------------

    if result["needs_research"]:
        assert "rag_result" in result

        assert (
            result["rag_result"].finding_id
            == TEST_FINDING_ID
        )

        assert "intelligence_result" in result

        assert (
            result[
                "intelligence_result"
            ].finding_id
            == TEST_FINDING_ID
        )

        print(
            "[PASS] research route"
        )

    else:
        assert (
            "rag_result"
            not in result
        )

        assert (
            "intelligence_result"
            not in result
        )

        print(
            "[PASS] research skip route"
        )

    # --------------------------------------------------
    # Evidence Assessment
    # --------------------------------------------------

    assert (
        "evidence_assessment"
        in result
    )

    evidence = result[
        "evidence_assessment"
    ]

    assert (
        evidence.finding_category
        in {
            "information_observation",
            "security_misconfiguration",
            "exposure",
            "vulnerability",
            "ambiguous_security_signal",
        }
    )

    assert (
        evidence.evidence_status
        in {
            "confirmed",
            "insufficient",
            "contradicted",
        }
    )

    assert (
        evidence.preliminary_verdict
        in {
            "likely_true_positive",
            "likely_false_positive",
            "needs_review",
        }
    )

    assert (
        0.0
        <= evidence.confidence
        <= 1.0
    )

    print(
        "[PASS] evidence assessment"
    )

    # --------------------------------------------------
    # Risk Enrichment
    # --------------------------------------------------

    assert (
        "risk_enrichment"
        in result
    )

    risk_enrichment = result[
        "risk_enrichment"
    ]

    assert (
        risk_enrichment
        is not None
    )

    print(
        "[PASS] risk enrichment"
    )

     # --------------------------------------------------
    # Grounding Validation
    # --------------------------------------------------

    assert (
        "grounding_result"
        in result
    )

    grounding = result[
        "grounding_result"
    ]

    assert (
        grounding.finding_id
        == TEST_FINDING_ID
    )

    assert (
        grounding.status
        in {
            "supported",
            "partially_supported",
            "unsupported",
        }
    )

    assert (
        0.0
        <= grounding.score
        <= 1.0
    )

    assert (
        grounding.original_verdict
        == result[
            "risk_enrichment"
        ].final_verdict
    )

    print(
        "[PASS] grounding validation"
    )

    # --------------------------------------------------
    # Final Workflow State
    # --------------------------------------------------

    assert (
        result["status"]
        == "grounding_completed"
    )

    assert (
        result.get("error")
        is None
    )

    assert (
        result.get("failed_node")
        is None
    )

    print(
        "[PASS] final workflow state"
    )

    print(
        "\nInvestigation Graph evaluation PASSED"
    )

if __name__ == "__main__":
    main()