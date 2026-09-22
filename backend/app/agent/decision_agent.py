from app.schemas.agent_decision import (
    AgentDecisionInput,
    AgentDecisionOutput,
)


MIN_ACTION_CONFIDENCE = 0.80

HIGH_RISK_LEVELS = {
    "high",
    "critical",
}

HIGH_SEVERITIES = {
    "high",
    "critical",
}


def _is_high_risk(
    data: AgentDecisionInput,
) -> bool:
    """
    判断 Finding 是否具有高风险信号。
    """

    severity = data.severity.lower()
    risk_level = data.risk_level.lower()

    return (
        severity in HIGH_SEVERITIES
        or risk_level in HIGH_RISK_LEVELS
        or data.risk_score >= 70
    )


def _review_priority(
    data: AgentDecisionInput,
) -> str:
    """
    人工复核时保留原始风险信号。

    高风险 Finding 不应因为进入 manual review
    就被统一降为 medium priority。
    """

    if _is_high_risk(data):
        return "high"

    return "medium"


def make_security_decision(
    data: AgentDecisionInput,
) -> AgentDecisionOutput:
    """
    根据 AI Verdict、置信度和风险信息生成处置建议。

    Agent 只生成决策建议，不直接修改 Finding 状态，
    也不执行真实修复操作。
    """

    verdict = data.verdict.lower()

    high_risk = _is_high_risk(data)

    # 1. 低置信度结果统一进入人工复核
    if data.confidence < MIN_ACTION_CONFIDENCE:
        return AgentDecisionOutput(
            action="request_manual_review",
            priority=_review_priority(data),
            reason=(
                "The AI analysis confidence is below the "
                "automatic decision threshold."
            ),
            requires_human_review=True,
            recommended_next_step=(
                "Ask a security analyst to validate the "
                "finding evidence and AI reasoning."
            ),
        )

    # 2. Informational 与高风险信号冲突
    if verdict == "informational":
        if high_risk:
            return AgentDecisionOutput(
                action="request_manual_review",
                priority="high",
                reason=(
                    "The informational verdict conflicts with "
                    "high-risk severity or risk signals."
                ),
                requires_human_review=True,
                recommended_next_step=(
                    "Review the finding classification and "
                    "risk evidence before closing it."
                ),
            )

        return AgentDecisionOutput(
            action="close_as_info",
            priority="low",
            reason=(
                "The AI analysis classified this finding "
                "as informational with sufficient confidence."
            ),
            requires_human_review=False,
            recommended_next_step=(
                "Record the finding as informational and "
                "retain it for asset visibility."
            ),
        )

    # 3. False Positive 与高风险信号冲突
    if verdict == "likely_false_positive":
        if high_risk:
            return AgentDecisionOutput(
                action="request_manual_review",
                priority="high",
                reason=(
                    "The false-positive verdict conflicts with "
                    "high-risk severity or risk signals."
                ),
                requires_human_review=True,
                recommended_next_step=(
                    "Ask a security analyst to verify the "
                    "evidence before suppressing the finding."
                ),
            )

        return AgentDecisionOutput(
            action="mark_false_positive",
            priority="low",
            reason=(
                "The finding was assessed as a likely false "
                "positive with sufficient confidence."
            ),
            requires_human_review=False,
            recommended_next_step=(
                "Mark the finding as a likely false positive "
                "and retain the decision for audit."
            ),
        )

    # 4. Needs Review
    if verdict == "needs_review":
        return AgentDecisionOutput(
            action="request_manual_review",
            priority=_review_priority(data),
            reason=(
                "The available evidence requires manual "
                "security review."
            ),
            requires_human_review=True,
            recommended_next_step=(
                "Ask a security analyst to review the finding "
                "evidence and AI reasoning."
            ),
        )

    # 5. Likely True Positive
    if verdict == "likely_true_positive":
        return AgentDecisionOutput(
            action="recommend_remediation",
            priority="high" if high_risk else "medium",
            reason=(
                "The finding was assessed as a likely true "
                "positive and should enter remediation review."
            ),
            requires_human_review=True,
            recommended_next_step=(
                "Review the confirmed evidence, determine the "
                "affected asset scope, and prioritize remediation."
            ),
        )

    # 6. 未知 Verdict：Fail Closed / Fail Safe
    return AgentDecisionOutput(
        action="request_manual_review",
        priority=_review_priority(data),
        reason=(
            f"Unsupported AI verdict received: {data.verdict}."
        ),
        requires_human_review=True,
        recommended_next_step=(
            "Ask a security analyst to review the finding "
            "before taking further action."
        ),
    )