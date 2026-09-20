from dataclasses import dataclass, field
from typing import Any


@dataclass
class SecurityDocument:
    """
    SentinelAgent RAG 中使用的统一安全知识文档结构。
    """

    id: str
    title: str
    content: str

    source: str
    category: str

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        将 SecurityDocument 转换为可序列化字典。
        """
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "category": self.category,
            "metadata": self.metadata,
        }