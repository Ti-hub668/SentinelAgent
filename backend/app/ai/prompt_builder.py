from app.schemas.ai_analysis import AIAnalysisInput


def build_risk_analysis_prompt(
    data: AIAnalysisInput
) -> str:
    """
    构造安全风险分析 Prompt。
    要求模型只返回结构化 JSON。
    """

    prompt = f"""
你是一名网络安全分析师。

请严格基于下面提供的安全发现进行风险研判。

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

1. 判断该结果属于以下哪一种：
   - informational
   - likely_true_positive
   - likely_false_positive
   - needs_review

2. 给出 0 到 1 之间的置信度。

3. 简要总结该安全发现。

4. 解释为什么存在或不存在实际安全风险。

5. 给出下一步处置建议。

安全约束：

- 不要编造不存在的漏洞。
- 不要编造 CVE 编号。
- 不要编造不存在的攻击行为。
- 不要将技术识别结果直接等同于漏洞。
- 如果证据不足，必须明确说明证据不足。
- 只能依据提供的信息进行判断。

只返回合法 JSON。
不要返回 Markdown。
不要使用 ```json 代码块。
不要在 JSON 前后添加任何说明文字。

必须严格使用下面的结构：

{{
  "verdict": "informational",
  "confidence": 0.95,
  "summary": "简要总结",
  "risk_explanation": "风险解释",
  "recommended_action": "处置建议"
}}
""".strip()

    return prompt