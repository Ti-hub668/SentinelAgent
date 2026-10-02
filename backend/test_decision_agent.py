from app.agent.decision_agent import make_security_decision
from app.schemas.agent_decision import AgentDecisionInput


test_cases = [
    {
        "name": "Informational",
        "verdict": "informational",
        "confidence": 0.95,
        "severity": "info",
        "risk_score": 10,
        "risk_level": "low",
    },
    {
        "name": "High-confidence False Positive",
        "verdict": "likely_false_positive",
        "confidence": 0.90,
        "severity": "medium",
        "risk_score": 20,
        "risk_level": "low",
    },
    {
        "name": "Needs Review",
        "verdict": "needs_review",
        "confidence": 0.60,
        "severity": "medium",
        "risk_score": 45,
        "risk_level": "medium",
    },
    {
        "name": "True Positive",
        "verdict": "likely_true_positive",
        "confidence": 0.95,
        "severity": "high",
        "risk_score": 80,
        "risk_level": "high",
    },
]


for index, case in enumerate(test_cases, start=1):
    data = AgentDecisionInput(
        finding_id=index,
        ai_analysis_id=index,
        verdict=case["verdict"],
        confidence=case["confidence"],
        severity=case["severity"],
        risk_score=case["risk_score"],
        risk_level=case["risk_level"],
    )

    result = make_security_decision(data)

    print("=" * 60)
    print(f"Case: {case['name']}")
    print(f"Verdict: {case['verdict']}")
    print(f"Action: {result.action}")
    print(f"Priority: {result.priority}")
    print(f"Human Review: {result.requires_human_review}")
    print(f"Reason: {result.reason}")
    print(f"Next Step: {result.recommended_next_step}")