from app.schemas.ai_analysis import (
    AIAnalysisInput,
    AIAnalysisResult
)


def analyze_finding(
    data: AIAnalysisInput
) -> AIAnalysisResult:
    """
    Mock AI Risk Analyst。

    Day 7 暂时使用规则模拟 AI 输出。
    Day 8 再替换为真实大模型调用。
    """

    if (
        data.risk_level == "low"
        and "technology detection" in data.title.lower()
    ):
        return AIAnalysisResult(
            verdict="informational",
            confidence=0.95,
            summary="该结果主要用于识别目标技术栈。",
            risk_explanation=(
                "当前发现属于信息级技术识别结果，"
                "未提供可利用漏洞或异常行为证据。"
            ),
            recommended_action=(
                "保留该结果作为资产指纹信息，"
                "继续结合其他漏洞扫描结果进行研判。"
            )
        )

    if data.risk_level in ("high", "critical"):
        return AIAnalysisResult(
            verdict="likely_true_positive",
            confidence=0.85,
            summary="该安全发现具有较高风险，需要优先检查。",
            risk_explanation=(
                "规则引擎已将该发现评估为高风险，"
                "应结合证据进一步验证实际可利用性。"
            ),
            recommended_action=(
                "优先进行人工复核，确认影响范围，"
                "并根据验证结果执行修复或缓解措施。"
            )
        )

    return AIAnalysisResult(
        verdict="needs_review",
        confidence=0.70,
        summary="当前信息不足以完成明确风险定性。",
        risk_explanation=(
            "已有扫描结果提供了一定风险信号，"
            "但仍缺少足够证据判断是否具有实际影响。"
        ),
        recommended_action=(
            "结合资产暴露情况、服务版本及其他扫描结果进一步核查。"
        )
    )