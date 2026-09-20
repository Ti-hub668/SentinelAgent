from typing import Any


def build_finding_query(
    finding: Any,
    max_evidence_length: int = 1000,
) -> str:
    """
    根据 SentinelAgent Finding 构造 RAG 检索 Query。

    同时兼容：
    - SQLAlchemy Finding 对象
    - dict 测试数据
    """

    def get_value(name: str) -> Any:
        if isinstance(finding, dict):
            return finding.get(name)

        return getattr(finding, name, None)

    title = get_value("title")
    finding_type = get_value("finding_type")
    severity = get_value("severity")
    description = get_value("description")
    evidence = get_value("evidence")

    parts: list[str] = []

    if title:
        parts.append(
            f"Finding title: {title}"
        )

    if finding_type:
        parts.append(
            f"Finding type: {finding_type}"
        )

    if severity:
        parts.append(
            f"Severity: {severity}"
        )

    if description:
        parts.append(
            f"Description: {description}"
        )

    if evidence:
        evidence_text = str(evidence)

        if len(evidence_text) > max_evidence_length:
            evidence_text = (
                evidence_text[:max_evidence_length]
                + "..."
            )

        parts.append(
            f"Evidence: {evidence_text}"
        )

    if not parts:
        raise ValueError(
            "Finding does not contain usable retrieval fields."
        )

    return "\n".join(parts)