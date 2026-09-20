import json
from pathlib import Path

from app.rag.document import SecurityDocument


def load_security_documents(file_path: str | Path) -> list[SecurityDocument]:
    """
    从 JSON 文件加载 SentinelAgent 安全知识文档。
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Knowledge file does not exist: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        raw_documents = json.load(file)

    if not isinstance(raw_documents, list):
        raise ValueError(
            "Knowledge JSON root must be a list."
        )

    documents: list[SecurityDocument] = []

    for index, item in enumerate(raw_documents):
        if not isinstance(item, dict):
            raise ValueError(
                f"Knowledge item at index {index} must be an object."
            )

        required_fields = {
            "id",
            "title",
            "content",
            "source",
            "category",
        }

        missing_fields = required_fields - item.keys()

        if missing_fields:
            raise ValueError(
                f"Knowledge item at index {index} "
                f"is missing fields: {sorted(missing_fields)}"
            )

        document = SecurityDocument(
            id=item["id"],
            title=item["title"],
            content=item["content"],
            source=item["source"],
            category=item["category"],
            metadata=item.get("metadata", {}),
        )

        documents.append(document)

    return documents