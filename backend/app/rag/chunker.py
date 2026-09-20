from app.rag.document import SecurityDocument


def chunk_document(
    document: SecurityDocument,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[SecurityDocument]:
    """
    将 SecurityDocument 的 content 按字符长度切分为多个 Chunk。
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be smaller than chunk_size."
        )

    content = document.content.strip()

    if not content:
        return []

    chunks: list[SecurityDocument] = []

    start = 0
    chunk_index = 0

    while start < len(content):
        end = min(start + chunk_size, len(content))
        chunk_text = content[start:end].strip()

        if chunk_text:
            chunk = SecurityDocument(
                id=f"{document.id}_chunk_{chunk_index}",
                title=document.title,
                content=chunk_text,
                source=document.source,
                category=document.category,
                metadata={
                    **document.metadata,
                    "parent_id": document.id,
                    "chunk_index": chunk_index,
                },
            )

            chunks.append(chunk)

        if end >= len(content):
            break

        start = end - chunk_overlap
        chunk_index += 1

    return chunks


def chunk_documents(
    documents: list[SecurityDocument],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[SecurityDocument]:
    """
    批量切分 SecurityDocument。
    """

    chunks: list[SecurityDocument] = []

    for document in documents:
        chunks.extend(
            chunk_document(
                document=document,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )

    return chunks