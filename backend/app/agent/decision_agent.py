from app.schemas.agent_decision import (
    AgentDecisionInput,
    AgentDecisionOutput,
)


def make_security_decision(
    data: AgentDecisionInput,
) -> AgentDecisionOutput:
    """
    根据 AI 研判结果和风险信息生成下一步处置建议。

    当前阶段只生成决策建议，不自动修改 Finding，
    也不执行真实修复操作。
    """

    verdict = data.verdict.lower()
    severity = data.severity.lower()
    risk_level = data.risk_level.lower()

    # 1. 信息类发现
    if verdict == "informational":
        return AgentDecisionOutput(
            action="close_as_info",
            priority="low",
            reason=(
                "The AI analysis classified this finding "
                "as informational."
            ),
            requires_human_review=False,
            recommended_next_step=(
                "Record the finding as informational and "
                "keep it for asset visibility."
            ),
        )

    # 2. 高置信度误报
    if (
        verdict == "likely_false_positive"
        and data.confidence >= 0.80
    ):
        return AgentDecisionOutput(
            action="mark_false_positive",
            priority="low",
            reason=(
                "The finding was assessed as a likely false "
                "positive with high confidence."
            ),
            requires_human_review=False,
            recommended_next_step=(
                "Mark the finding as a likely false positive "
                "and retain the analysis for audit."
            ),
        )

    # 3. 证据不足，或者低置信度误报
    if (
        verdict == "needs_review"
        or verdict == "likely_false_positive"
    ):
        return AgentDecisionOutput(
            action="request_manual_review",
            priority="medium",
            reason=(
                "The available evidence is not sufficient for "
                "safe automatic classification."
            ),
            requires_human_review=True,
            recommended_next_step=(
                "Ask a security analyst to review the finding "
                "evidence and AI reasoning."
            ),
        )

    # 4. Likely True Positive
    if verdict == "likely_true_positive":

        high_risk = (
            severity in {"high", "critical"}
            or risk_level in {"high", "critical"}
            or data.risk_score >= 70
        )

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

    # 5. 防御性兜底
    return AgentDecisionOutput(
        action="request_manual_review",
        priority="medium",
        reason=(
            f"Unsupported AI verdict received: {data.verdict}."
        ),
        requires_human_review=True,
        recommended_next_step=(
            "Ask a security analyst to review the finding "
            "before taking further action."
        ),
    )