import re
from pathlib import Path

from app.rag.document import (
    SecurityDocument,
)

from app.rag.vector_store import (
    InMemoryVectorStore,
    SearchResult,
)


DEFAULT_INDEX_PATH = Path(
    "knowledge/vector_store/"
    "security_index.json"
)


IDENTIFIER_PATTERNS = [
    re.compile(
        r"\bCVE-\d{4}-\d{4,}\b",
        re.IGNORECASE,
    ),

    re.compile(
        r"\bCWE-\d+\b",
        re.IGNORECASE,
    ),

    re.compile(
        r"\bCAPEC-\d+\b",
        re.IGNORECASE,
    ),

    re.compile(
        r"\bT\d{4}(?:\.\d{3})?\b",
        re.IGNORECASE,
    ),
]


RELATED_IDENTIFIER_KEYS = [
    "cve_ids",
    "cwe_ids",
    "attack_ids",
    "related_cwes",
    "related_capec",
    "attack_mappings",
    "technique_id",
    "external_id",
]


def extract_identifiers(
    text: str,
) -> set[str]:
    """
    Extract canonical security identifiers from text.
    """

    identifiers: set[str] = set()

    for pattern in IDENTIFIER_PATTERNS:
        for match in pattern.findall(
            text
        ):
            identifiers.add(
                match.upper()
            )

    return identifiers


def _metadata_values(
    value,
) -> list[str]:
    """
    Convert metadata values into strings that
    can be inspected for security identifiers.
    """

    if value is None:
        return []

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            str(item)
            for item in value
            if item is not None
        ]

    return [
        str(value)
    ]


def primary_document_identifiers(
    document: SecurityDocument,
) -> set[str]:
    """
    Return identifiers that identify the document itself.

    Examples:
    - CWE-79 document -> CWE-79
    - CAPEC-63 document -> CAPEC-63
    - ATT&CK document -> T1059.003

    Relationship identifiers are intentionally excluded.
    """

    metadata = (
        document.metadata
        or {}
    )

    values = [
        document.id,
        document.title,
    ]

    source_id = metadata.get(
        "source_id"
    )

    if source_id:
        values.append(
            str(source_id)
        )

    return extract_identifiers(
        " ".join(values)
    )


def related_document_identifiers(
    document: SecurityDocument,
) -> set[str]:
    """
    Return identifiers referenced by the document
    but which are not its own canonical identifier.

    Examples:
    - CWE-79 -> related CAPEC IDs
    - CAPEC-1 -> related CWE / ATT&CK IDs
    """

    metadata = (
        document.metadata
        or {}
    )

    values: list[str] = []

    for key in RELATED_IDENTIFIER_KEYS:
        values.extend(
            _metadata_values(
                metadata.get(
                    key
                )
            )
        )

    identifiers = extract_identifiers(
        " ".join(values)
    )

    # An adapter may duplicate its own source ID
    # inside cwe_ids / attack_ids. Do not treat
    # that as a relationship.
    return (
        identifiers
        - primary_document_identifiers(
            document
        )
    )


class SecurityKnowledgeRetriever:
    """
    SentinelAgent hybrid security knowledge retriever.

    Ranking priority:

    1. Canonical / primary identifier match
    2. Relationship identifier match
    3. Semantic vector similarity
    """

    PRIMARY_EXACT_BASE = 2.0

    RELATED_EXACT_BASE = 1.2

    def __init__(
        self,
        index_path: str | Path = (
            DEFAULT_INDEX_PATH
        ),
    ) -> None:

        self.index_path = Path(
            index_path
        )

        self.store = (
            InMemoryVectorStore.load(
                self.index_path
            )
        )

    @staticmethod
    def _semantic_bonus(
        score: float,
    ) -> float:
        """
        Keep semantic relevance as a small
        tie breaker for identifier matches.
        """

        normalized = max(
            0.0,
            min(
                float(score),
                1.0,
            ),
        )

        return (
            normalized
            * 0.05
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[SearchResult]:

        query = query.strip()

        if not query:
            raise ValueError(
                "Retrieval query "
                "cannot be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be "
                "greater than 0."
            )

        query_identifiers = (
            extract_identifiers(
                query
            )
        )

        candidate_k = max(
            top_k * 12,
            48,
        )

        semantic_results = (
            self.store.search(
                query=query,
                top_k=candidate_k,
            )
        )

        merged: dict[
            str,
            SearchResult,
        ] = {}

        # ---------------------------------
        # Phase 1
        # Semantic candidates + ID rerank
        # ---------------------------------

        for result in semantic_results:

            document = (
                result.document
            )

            primary_ids = (
                primary_document_identifiers(
                    document
                )
            )

            related_ids = (
                related_document_identifiers(
                    document
                )
            )

            primary_match = bool(
                query_identifiers
                & primary_ids
            )

            related_match = bool(
                query_identifiers
                & related_ids
            )

            if primary_match:
                score = (
                    self.PRIMARY_EXACT_BASE
                    + self._semantic_bonus(
                        result.score
                    )
                )

            elif related_match:
                score = (
                    self.RELATED_EXACT_BASE
                    + self._semantic_bonus(
                        result.score
                    )
                )

            else:
                score = (
                    result.score
                )

            merged[
                document.id
            ] = SearchResult(
                document=document,
                score=score,
            )

        # ---------------------------------
        # Phase 2
        # Guarantee canonical exact anchors
        # ---------------------------------

        if query_identifiers:

            for document in (
                self.store.documents()
            ):

                chunk_index = (
                    document.metadata
                    .get(
                        "chunk_index"
                    )
                )

                # Only inject the anchor chunk.
                # Other chunks can still appear
                # through semantic retrieval.
                if chunk_index not in (
                    0,
                    None,
                ):
                    continue

                primary_ids = (
                    primary_document_identifiers(
                        document
                    )
                )

                if not (
                    query_identifiers
                    & primary_ids
                ):
                    continue

                current = merged.get(
                    document.id
                )

                exact_score = (
                    self.PRIMARY_EXACT_BASE
                )

                if (
                    current is None
                    or current.score
                    < exact_score
                ):
                    merged[
                        document.id
                    ] = SearchResult(
                        document=document,
                        score=exact_score,
                    )

        # ---------------------------------
        # Phase 3
        # Ranking
        # ---------------------------------

        ranked = sorted(
            merged.values(),
            key=lambda item:
                item.score,
            reverse=True,
        )

        selected: list[
            SearchResult
        ] = []

        parent_counts: dict[
            str,
            int,
        ] = {}

        for result in ranked:

            document = (
                result.document
            )

            parent_id = str(
                document.metadata.get(
                    "parent_id",
                    document.id,
                )
            )

            count = (
                parent_counts.get(
                    parent_id,
                    0,
                )
            )

            # Exact canonical matches only need
            # one anchor chunk in the Top-K.
            #
            # Semantic / relationship matches may
            # contribute up to two useful chunks.
            if (
                result.score
                >= self.PRIMARY_EXACT_BASE
            ):
                max_parent_chunks = 1

            else:
                max_parent_chunks = 2

            if (
                count
                >= max_parent_chunks
            ):
                continue

            selected.append(
                result
            )

            parent_counts[
                parent_id
            ] = count + 1

            if (
                len(selected)
                >= top_k
            ):
                break

        return selected