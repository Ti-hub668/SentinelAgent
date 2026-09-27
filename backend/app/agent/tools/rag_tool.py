from app.models.finding import Finding
from app.rag.context_builder import build_rag_context
from app.rag.query_builder import build_finding_query
from app.rag.retriever import SecurityKnowledgeRetriever
from app.schemas.agent_tools import (
    RAGToolResult,
    SecurityKnowledgeItem,
)
from app.schemas.investigation_context import SentinelContextBundle

def retrieve_security_knowledge(
    finding: Finding,
    top_k: int = 3,
) -> RAGToolResult:
    """
    Retrieve relevant local security knowledge for one Finding.

    This tool adapts SentinelAgent's existing RAG pipeline into a
    stable typed contract for the future Agent workflow.
    """

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    query = build_finding_query(
        finding
    )

    retriever = SecurityKnowledgeRetriever()

    results = retriever.retrieve(
        query=query,
        top_k=top_k,
    )

    prompt_context = build_rag_context(
        results
    )

    items = [
        SecurityKnowledgeItem(
            document_id=result.document.id,
            title=result.document.title,
            source=result.document.source,
            category=result.document.category,
            score=result.score,
            content=result.document.content,
            metadata=result.document.metadata,
        )
        for result in results
    ]

    return RAGToolResult(
        finding_id=finding.id,
        query=query,
        results=items,
        prompt_context=prompt_context,
    )

def retrieve_context_knowledge(
    context: SentinelContextBundle,
    top_k: int = 3,
) -> RAGToolResult:
    """
    Retrieve security knowledge directly from an investigation context.

    LangGraph nodes should prefer this interface because it avoids
    additional database reads after the ContextBundle has been built.
    """

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    finding_data = context.finding.model_dump()

    query = build_finding_query(
        finding_data
    )

    retriever = SecurityKnowledgeRetriever()

    results = retriever.retrieve(
        query=query,
        top_k=top_k,
    )

    prompt_context = build_rag_context(
        results
    )

    items = [
        SecurityKnowledgeItem(
            document_id=result.document.id,
            title=result.document.title,
            source=result.document.source,
            category=result.document.category,
            score=result.score,
            content=result.document.content,
            metadata=result.document.metadata,
        )
        for result in results
    ]

    return RAGToolResult(
        finding_id=context.finding_id,
        query=query,
        results=items,
        prompt_context=prompt_context,
    )