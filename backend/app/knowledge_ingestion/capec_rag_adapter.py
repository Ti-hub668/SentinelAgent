import json
from pathlib import Path

from app.knowledge_ingestion.schema import (
    SecurityKnowledgeRecord,
)

from app.rag.document import (
    SecurityDocument,
)


CAPEC_PROCESSED_PATH = Path(
    "knowledge/processed/capec.json"
)

CAPEC_RAG_PATH = Path(
    "knowledge/raw/mitre_capec.json"
)


def load_capec_records(
    path: Path = (
        CAPEC_PROCESSED_PATH
    ),
) -> list[
    SecurityKnowledgeRecord
]:

    if not path.exists():
        raise FileNotFoundError(
            "Normalized CAPEC dataset "
            f"not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(
            file
        )

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            "CAPEC normalized root "
            "must be a list."
        )

    return [
        SecurityKnowledgeRecord(
            **item
        )
        for item in data
    ]


def build_capec_content(
    record:
        SecurityKnowledgeRecord,
) -> str:

    metadata = (
        record.metadata
        or {}
    )

    parts = [
        (
            "CAPEC Identifier: "
            f"{record.source_id}"
        ),

        (
            "Attack Pattern: "
            f"{record.title}"
        ),

        (
            "Description: "
            f"{record.description}"
        ),
    ]

    abstraction = (
        metadata.get(
            "abstraction"
        )
    )

    if abstraction:
        parts.append(
            "Abstraction: "
            f"{abstraction}"
        )

    likelihood = (
        metadata.get(
            "likelihood_of_attack"
        )
    )

    if likelihood:
        parts.append(
            "Likelihood of Attack: "
            f"{likelihood}"
        )

    severity = (
        metadata.get(
            "typical_severity"
        )
    )

    if severity:
        parts.append(
            "Typical Severity: "
            f"{severity}"
        )

    cwe_ids = (
        record.cwe_ids
    )

    if cwe_ids:
        parts.append(
            "Related CWE IDs: "
            + ", ".join(
                cwe_ids
            )
        )

    prerequisites = (
        metadata.get(
            "prerequisites",
            [],
        )
    )

    if prerequisites:
        parts.append(
            "Prerequisites:\n- "
            + "\n- ".join(
                prerequisites
            )
        )

    execution_flow = (
        metadata.get(
            "execution_flow",
            [],
        )
    )

    if execution_flow:
        parts.append(
            "Execution Flow:\n- "
            + "\n- ".join(
                execution_flow
            )
        )

    consequences = (
        metadata.get(
            "consequences",
            [],
        )
    )

    if consequences:
        parts.append(
            "Consequences:\n- "
            + "\n- ".join(
                consequences
            )
        )

    mitigations = (
        metadata.get(
            "mitigations",
            [],
        )
    )

    if mitigations:
        parts.append(
            "Mitigations:\n- "
            + "\n- ".join(
                mitigations
            )
        )

    indicators = (
        metadata.get(
            "indicators",
            [],
        )
    )

    if indicators:
        parts.append(
            "Indicators:\n- "
            + "\n- ".join(
                indicators
            )
        )

    related_capec = (
        metadata.get(
            "related_capec",
            [],
        )
    )

    if related_capec:
        parts.append(
            "Related CAPEC IDs: "
            + ", ".join(
                related_capec
            )
        )

    if record.attack_ids:
        parts.append(
            "ATT&CK Techniques: "
            + ", ".join(
                record.attack_ids
            )
        )

    return "\n\n".join(
        parts
    )


def to_security_document(
    record:
        SecurityKnowledgeRecord,
) -> SecurityDocument:

    return SecurityDocument(
        id=(
            "mitre_capec:"
            f"{record.source_id}"
        ),

        title=(
            f"{record.source_id} "
            f"{record.title}"
        ),

        content=(
            build_capec_content(
                record
            )
        ),

        source="MITRE CAPEC",

        category=(
            "attack_pattern"
        ),

        metadata={
            "source_id":
                record.source_id,

            "cwe_ids":
                record.cwe_ids,

            "attack_ids":
                record.attack_ids,

            "source_url":
                record.source_url,

            **(
                record.metadata
                or {}
            ),
        },
    )


def build_capec_rag_documents(
    input_path: Path = (
        CAPEC_PROCESSED_PATH
    ),
) -> list[
    SecurityDocument
]:

    records = (
        load_capec_records(
            input_path
        )
    )

    return [
        to_security_document(
            record
        )
        for record in records
    ]


def save_rag_documents(
    documents: list[
        SecurityDocument
    ],

    output_path: Path = (
        CAPEC_RAG_PATH
    ),
) -> Path:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = [
        document.to_dict()
        for document in documents
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


def main() -> None:

    documents = (
        build_capec_rag_documents()
    )

    output_path = (
        save_rag_documents(
            documents
        )
    )

    print()
    print("=" * 60)
    print(
        "MITRE CAPEC RAG Adapter"
    )
    print("=" * 60)

    print(
        f"Documents : "
        f"{len(documents)}"
    )

    print(
        f"Saved     : "
        f"{output_path}"
    )

    if documents:
        print()
        print(
            f"First ID  : "
            f"{documents[0].id}"
        )

        print(
            f"Title     : "
            f"{documents[0].title}"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()