from typing import Any

from pydantic import BaseModel, Field


class SecurityKnowledgeItem(BaseModel):
    document_id: str
    title: str
    source: str
    category: str

    score: float

    content: str

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

class SecurityKnowledgeEvidence(BaseModel):
    """
    Compact provenance record for one retrieved
    security knowledge chunk.

    This structure is designed for the
    Investigation Ledger.
    """

    document_id: str

    parent_id: str | None = None

    source_id: str | None = None

    title: str

    source: str

    category: str

    score: float

    match_type: str

    chunk_index: int | None = None

    source_url: str | None = None

    content_sha256: str

class RAGToolResult(BaseModel):
    finding_id: int

    query: str

    results: list[SecurityKnowledgeItem] = Field(
        default_factory=list
    )

    prompt_context: str

    # ---------- Retrieval provenance ----------

    index_path: str | None = None

    retrieval_strategy: str = (
        "hybrid_v2"
    )

    top_k: int = Field(
        default=3,
        ge=1,
    )

    retrieved_sources: list[str] = Field(
        default_factory=list
    )

    evidence: list[
        SecurityKnowledgeEvidence
    ] = Field(
        default_factory=list
    )


class KEVRecordContext(BaseModel):
    cve_id: str

    known_exploited: bool

    title: str | None = None

    affected_products: list[str] = Field(
        default_factory=list
    )

    cwe_ids: list[str] = Field(
        default_factory=list
    )

    required_action: str | None = None

    date_added: str | None = None

    due_date: str | None = None

    known_ransomware_campaign_use: str | None = None


class NVDRecordContext(BaseModel):
    cve_id: str

    description: str | None = None

    cvss_score: float | None = None

    severity: str | None = None

    cwe_ids: list[str] = Field(
        default_factory=list
    )

    affected_products: list[str] = Field(
        default_factory=list
    )

    references: list[str] = Field(
        default_factory=list
    )

    published_at: str | None = None

    modified_at: str | None = None

    vuln_status: str | None = None


class VulnerabilityIntelligenceResult(BaseModel):
    finding_id: int

    template_id: str | None = None

    cve_ids: list[str] = Field(
        default_factory=list
    )

    cwe_ids: list[str] = Field(
        default_factory=list
    )

    kev_matched: bool = False

    kev_records: list[KEVRecordContext] = Field(
        default_factory=list
    )

    nvd_matched: bool = False

    nvd_records: list[NVDRecordContext] = Field(
        default_factory=list
    )