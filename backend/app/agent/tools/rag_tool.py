import hashlib
import os
from pathlib import Path

from app.models.finding import Finding
from app.rag.context_builder import (
    build_rag_context,
)
from app.rag.query_builder import (
    build_finding_query,
)
from app.rag.retriever import (
    SecurityKnowledgeRetriever,
)
from app.rag.vector_store import SearchResult
from app.schemas.agent_tools import (
    RAGToolResult,
    SecurityKnowledgeEvidence,
    SecurityKnowledgeItem,
)
from app.schemas.investigation_context import (
    SentinelContextBundle,
)


DEFAULT_AGENT_RAG_INDEX_PATH = Path(
    "knowledge/vector_store/"
    "security_index_v4.json"
)

AGENT_RAG_INDEX_PATH = Path(
    os.getenv(
        "SENTINEL_RAG_INDEX_PATH",
        str(
            DEFAULT_AGENT_RAG_INDEX_PATH
        ),
    )
)


def _content_sha256(
    content: str,
) -> str:
    """
    Build a deterministic SHA-256 fingerprint
    for one retrieved knowledge chunk.
    """

    return hashlib.sha256(
        content.encode(
            "utf-8"
        )
    ).hexdigest()


def _detect_match_type(
    score: float,
) -> str:
    """
    Convert Hybrid Retriever v2 score bands
    into a human-readable provenance label.

    Current ranking policy:

    >= 2.0
        canonical exact identifier match

    >= 1.2
        relationship identifier match

    < 1.2
        semantic similarity match
    """

    if score >= 2.0:
        return "canonical_exact"

    if score >= 1.2:
        return "relationship"

    return "semantic"


def _build_knowledge_item(
    result: SearchResult,
) -> SecurityKnowledgeItem:
    """
    Convert one vector-store SearchResult into
    the typed Agent knowledge item.
    """

    document = result.document

    return SecurityKnowledgeItem(
        document_id=document.id,
        title=document.title,
        source=document.source,
        category=document.category,
        score=result.score,
        content=document.content,
        metadata=document.metadata,
    )


def _build_evidence_record(
    result: SearchResult,
) -> SecurityKnowledgeEvidence:
    """
    Convert one retrieved chunk into compact
    audit-safe evidence provenance.
    """

    document = result.document

    metadata = (
        document.metadata
        or {}
    )

    parent_id = metadata.get(
        "parent_id"
    )

    source_id = metadata.get(
        "source_id"
    )

    chunk_index = metadata.get(
        "chunk_index"
    )

    source_url = metadata.get(
        "source_url"
    )

    return SecurityKnowledgeEvidence(
        document_id=document.id,

        parent_id=(
            str(parent_id)
            if parent_id is not None
            else None
        ),

        source_id=(
            str(source_id)
            if source_id is not None
            else None
        ),

        title=document.title,

        source=document.source,

        category=document.category,

        score=result.score,

        match_type=(
            _detect_match_type(
                result.score
            )
        ),

        chunk_index=(
            int(chunk_index)
            if chunk_index is not None
            else None
        ),

        source_url=(
            str(source_url)
            if source_url is not None
            else None
        ),

        content_sha256=(
            _content_sha256(
                document.content
            )
        ),
    )


def _retrieve(
    *,
    finding_id: int,
    query: str,
    top_k: int,
) -> RAGToolResult:
    """
    Shared RAG execution path for both database
    Finding objects and SentinelContextBundle.

    Uses the configured production Agent index
    and returns both prompt context and auditable
    retrieval provenance.
    """

    retriever = (
        SecurityKnowledgeRetriever(
            index_path=(
                AGENT_RAG_INDEX_PATH
            )
        )
    )

    results = retriever.retrieve(
        query=query,
        top_k=top_k,
    )

    prompt_context = (
        build_rag_context(
            results
        )
    )

    items = [
        _build_knowledge_item(
            result
        )
        for result in results
    ]

    evidence = [
        _build_evidence_record(
            result
        )
        for result in results
    ]

    retrieved_sources = list(
        dict.fromkeys(
            result.document.source
            for result in results
        )
    )

    return RAGToolResult(
        finding_id=finding_id,

        query=query,

        results=items,

        prompt_context=
            prompt_context,

        index_path=str(
            AGENT_RAG_INDEX_PATH
        ),

        retrieval_strategy=(
            "hybrid_v2"
        ),

        top_k=top_k,

        retrieved_sources=
            retrieved_sources,

        evidence=evidence,
    )


def retrieve_security_knowledge(
    finding: Finding,
    top_k: int = 3,
) -> RAGToolResult:
    """
    Retrieve relevant local security knowledge
    for one Finding.

    This interface is useful outside the
    LangGraph investigation workflow.
    """

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    query = build_finding_query(
        finding
    )

    return _retrieve(
        finding_id=finding.id,
        query=query,
        top_k=top_k,
    )


def retrieve_context_knowledge(
    context: SentinelContextBundle,
    top_k: int = 3,
) -> RAGToolResult:
    """
    Retrieve security knowledge directly from
    an investigation context.

    LangGraph Research should prefer this path
    because it avoids another database read after
    SentinelContextBundle has been built.
    """

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    finding_data = (
        context.finding.model_dump()
    )

    query = build_finding_query(
        finding_data
    )

    return _retrieve(
        finding_id=context.finding_id,
        query=query,
        top_k=top_k,
    )