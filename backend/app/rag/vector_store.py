import json
import math
from dataclasses import dataclass
from pathlib import Path

from app.rag.document import SecurityDocument
from app.rag.embedding import embed_text


@dataclass
class SearchResult:
    document: SecurityDocument
    score: float


def cosine_similarity(
    vector_a: list[float],
    vector_b: list[float],
) -> float:
    """
    计算两个向量之间的余弦相似度。
    """

    if len(vector_a) != len(vector_b):
        raise ValueError(
            "Vectors must have the same dimension."
        )

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    norm_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    norm_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


class InMemoryVectorStore:
    """
    SentinelAgent 最小本地内存向量库。
    """

    def __init__(self) -> None:
        self._items: list[
            tuple[SecurityDocument, list[float]]
        ] = []

    def add_document(
        self,
        document: SecurityDocument,
    ) -> None:
        """
        对文档生成 Embedding 并加入向量库。
        """

        vector = embed_text(document.content)

        self._items.append(
            (document, vector)
        )

    def add_documents(
        self,
        documents: list[SecurityDocument],
    ) -> None:
        """
        批量加入文档。
        """

        for document in documents:
            self.add_document(document)

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[SearchResult]:
        """
        根据 Query 进行向量相似度检索。
        """

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        query_vector = embed_text(query)

        results: list[SearchResult] = []

        for document, document_vector in self._items:
            score = cosine_similarity(
                query_vector,
                document_vector,
            )

            results.append(
                SearchResult(
                    document=document,
                    score=score,
                )
            )

        results.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        return results[:top_k]
    def save(self, file_path: str | Path) -> None:
        """
        将当前向量索引保存到 JSON 文件。
        """

        path = Path(file_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = []   

        for document, vector in self._items:
            data.append(
                {
                    "document": document.to_dict(),
                    "vector": vector,
                }
            )

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
            )

    @classmethod
    def load(
        cls,
        file_path: str | Path,
    ) -> "InMemoryVectorStore":
        """
        从 JSON 文件加载已有向量索引。
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Vector index does not exist: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        store = cls()

        for item in data:
            document_data = item["document"]

            document = SecurityDocument(
                id=document_data["id"],
                title=document_data["title"],
                content=document_data["content"],
                source=document_data["source"],
                category=document_data["category"],
                metadata=document_data.get(
                    "metadata",
                    {},
                ),
            )

            vector = item["vector"]

            store._items.append(
                (document, vector)
            )

        return store