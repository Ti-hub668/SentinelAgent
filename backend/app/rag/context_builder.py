from app.rag.vector_store import SearchResult


def build_rag_context(
    results: list[SearchResult],
    max_content_length: int = 1200,
) -> str:
    """
    将 Top-K RAG 检索结果转换为可注入 LLM Prompt 的文本上下文。
    """

    if not results:
        return "No relevant security knowledge was retrieved."

    context_blocks: list[str] = []

    for index, result in enumerate(results, start=1):
        document = result.document

        content = document.content.strip()

        if len(content) > max_content_length:
            content = (
                content[:max_content_length]
                + "..."
            )

        block = (
            f"[Knowledge {index}]\n"
            f"Title: {document.title}\n"
            f"Category: {document.category}\n"
            f"Source: {document.source}\n"
            f"Similarity: {result.score:.4f}\n"
            f"Content: {content}"
        )

        context_blocks.append(block)

    return "\n\n".join(context_blocks)