from typing import Any, Literal

from pydantic import BaseModel, Field


KnowledgeSource = Literal[
    "nvd",
    "cisa_kev",
    "cwe",
    "mitre_attack",
]


KnowledgeType = Literal[
    "vulnerability",
    "weakness",
    "known_exploited_vulnerability",
    "attack_technique",
]


class SecurityKnowledgeRecord(BaseModel):
    """
    SentinelAgent unified schema for official security knowledge.

    External data from NVD, CISA KEV, CWE and MITRE ATT&CK
    is normalized into this structure before further processing.
    """

    # ---------- Identity ----------

    id: str = Field(
        description="Unique SentinelAgent knowledge record ID."
    )

    source: KnowledgeSource

    source_id: str = Field(
        description=(
            "Original identifier from the upstream source, "
            "for example CVE-2025-1234 or CWE-79."
        )
    )

    knowledge_type: KnowledgeType

    # ---------- Human-readable knowledge ----------

    title: str

    description: str

    remediation: str | None = None

    # ---------- Security classification ----------

    severity: str | None = None

    cvss_score: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
    )

    cwe_ids: list[str] = Field(
        default_factory=list
    )

    cve_ids: list[str] = Field(
        default_factory=list
    )

    attack_ids: list[str] = Field(
        default_factory=list
    )

    # ---------- Exploitation intelligence ----------

    known_exploited: bool = False

    # ---------- Product / technology context ----------

    affected_products: list[str] = Field(
        default_factory=list
    )

    # ---------- Provenance ----------

    source_url: str | None = None

    published_at: str | None = None

    modified_at: str | None = None

    retrieved_at: str | None = None

    # ---------- Retrieval ----------

    tags: list[str] = Field(
        default_factory=list
    )

    # ---------- Original source metadata ----------

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )