from pathlib import Path

from app.rag.chunker import chunk_documents
from app.rag.knowledge_loader import load_security_documents
from app.rag.vector_store import InMemoryVectorStore


DEFAULT_RAW_DIR = Path("knowledge/raw")

DEFAULT_INDEX_PATH = Path(
    "knowledge/vector_store/security_index.json"
)


def build_security_index(
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    output_path: str | Path = DEFAULT_INDEX_PATH,
) -> Path:
    """
    从 knowledge/raw 目录自动加载全部 JSON 安全知识，
    完成 Chunking、Embedding，并生成本地向量索引。
    """

    raw_dir = Path(raw_dir)
    output_path = Path(output_path)

    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Knowledge directory not found: {raw_dir}"
        )

    knowledge_files = sorted(
        raw_dir.glob("*.json")
    )

    if not knowledge_files:
        raise ValueError(
            f"No JSON knowledge files found in: {raw_dir}"
        )

    print("=" * 60)
    print("SentinelAgent Knowledge Index Builder")
    print("=" * 60)

    print(
        f"Knowledge directory: {raw_dir}"
    )

    print(
        f"Knowledge files: {len(knowledge_files)}"
    )

    all_documents = []

    for file_path in knowledge_files:
        documents = load_security_documents(
            file_path
        )

        all_documents.extend(
            documents
        )

        print(
            f"Loaded: {file_path.name} "
            f"({len(documents)} documents)"
        )

    document_ids = [
        document.id
        for document in all_documents
    ]

    duplicate_ids = sorted(
        {
            document_id
            for document_id in document_ids
            if document_ids.count(document_id) > 1
        }
    )

    if duplicate_ids:
        raise ValueError(
            "Duplicate knowledge document IDs: "
            + ", ".join(duplicate_ids)
        )

    chunks = chunk_documents(
        all_documents
    )

    print()
    print(
        f"Documents: {len(all_documents)}"
    )

    print(
        f"Chunks: {len(chunks)}"
    )

    print()
    print("Generating embeddings...")

    store = InMemoryVectorStore()

    store.add_documents(
        chunks
    )

    store.save(
        output_path
    )

    print()
    print(
        f"Vector entries: {len(chunks)}"
    )

    print(
        f"Index saved to: {output_path}"
    )

    print("=" * 60)

    return output_path


if __name__ == "__main__":
    build_security_index()