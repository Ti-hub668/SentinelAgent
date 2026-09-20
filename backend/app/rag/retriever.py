from pathlib import Path

from app.rag.vector_store import (
    InMemoryVectorStore,
    SearchResult,
)


DEFAULT_INDEX_PATH = Path(
    "knowledge/vector_store/security_index.json"
)


class SecurityKnowledgeRetriever:
    """
    SentinelAgent 安全知识检索器。
    """

    def __init__(
        self,
        index_path: str | Path = DEFAULT_INDEX_PATH,
    ) -> None:
        self.index_path = Path(index_path)
        self.store = InMemoryVectorStore.load(
            self.index_path
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[SearchResult]:
        """
        根据安全 Query 检索最相关的知识。
        """

        query = query.strip()

        if not query:
            raise ValueError(
                "Retrieval query cannot be empty."
            )

        return self.store.search(
            query=query,
            top_k=top_k,
        )