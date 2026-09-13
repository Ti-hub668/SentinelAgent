def calculate_risk(
    severity: str,
    finding_type: str,
    source: str,
    title: str = "",
    evidence: str = ""
) -> dict:
    """
    根据 Finding 信息计算基础风险评分。

    返回：
    {
        "risk_score": int,
        "risk_level": str,
        "risk_reason": str
    }
    """

    severity = (severity or "info").lower()
    finding_type = (finding_type or "").lower()
    source = (source or "").lower()
    title = (title or "").lower()
    evidence = (evidence or "").lower()

    severity_scores = {
        "info": 10,
        "low": 30,
        "medium": 50,
        "high": 75,
        "critical": 95,
    }

    score = severity_scores.get(severity, 10)

    reasons = [
        f"基础严重程度为 {severity}，初始风险分数为 {score}"
    ]

    if finding_type == "vulnerability":
        score += 5
        reasons.append("该发现属于漏洞类安全发现，风险分数增加 5")

    if source == "nuclei":
        reasons.append("该结果来源于 Nuclei 自动化安全扫描")

    if "technology detection" in title:
        score = min(score, 15)
        reasons.append(
            "当前结果主要属于技术识别信息，未直接表明存在可利用漏洞"
        )

    if "mysql" in title or "3306" in evidence:
        score += 10
        reasons.append(
            "检测信息涉及数据库服务，若对外暴露可能扩大攻击面"
        )

    score = max(0, min(score, 100))

    if score >= 90:
        risk_level = "critical"
    elif score >= 70:
        risk_level = "high"
    elif score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "risk_reason": "；".join(reasons)
    }