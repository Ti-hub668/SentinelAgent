from app.schemas.ai_analysis import AIAnalysisInput


def build_risk_analysis_prompt(
    data: AIAnalysisInput
) -> str:
    """
    构造安全风险分析 Prompt。
    """

    prompt = f"""
你是一名网络安全分析师。

请基于下面的安全发现进行风险研判。

安全发现信息：

Finding ID:
{data.finding_id}

来源:
{data.source}

类型:
{data.finding_type}

标题:
{data.title}

严重程度:
{data.severity}

目标:
{data.target}

描述:
{data.description or "无"}

证据:
{data.evidence or "无"}

已有规则风险评分:
{data.risk_score}

已有风险等级:
{data.risk_level}

已有规则判断依据:
{data.risk_reason or "无"}

请完成以下任务：

1. 判断该结果属于：
   - informational
   - likely_true_positive
   - likely_false_positive
   - needs_review

2. 给出 0 到 1 之间的置信度。

3. 用简洁语言总结该安全发现。

4. 解释为什么存在或不存在实际安全风险。

5. 给出下一步处置建议。

不要编造不存在的漏洞、CVE 或攻击证据。
仅根据给定信息进行分析。
""".strip()

    return prompt