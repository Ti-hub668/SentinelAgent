import json
from pathlib import Path

from app.knowledge_ingestion.schema import (
    SecurityKnowledgeRecord,
)

from app.rag.document import (
    SecurityDocument,
)


CWE_PROCESSED_PATH = Path(
    "knowledge/processed/cwe.json"
)

CWE_RAG_PATH = Path(
    "knowledge/raw/mitre_cwe.json"
)


def load_cwe_records(
    path: Path = CWE_PROCESSED_PATH,
) -> list[
    SecurityKnowledgeRecord
]:
    if not path.exists():
        raise FileNotFoundError(
            "Normalized CWE dataset "
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
            "CWE normalized root "
            "must be a list."
        )

    return [
        SecurityKnowledgeRecord(
            **item
        )
        for item in data
    ]


def build_cwe_content(
    record:
        SecurityKnowledgeRecord,
) -> str:

    metadata = (
        record.metadata
        or {}
    )

    parts = [
        (
            "CWE Identifier: "
            f"{record.source_id}"
        ),

        (
            "Weakness Name: "
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
            "likelihood_of_exploit"
        )
    )

    if likelihood:
        parts.append(
            "Likelihood of Exploit: "
            f"{likelihood}"
        )

    consequences = (
        metadata.get(
            "common_consequences",
            [],
        )
    )

    if consequences:
        parts.append(
            "Common Consequences:\n- "
            + "\n- ".join(
                consequences
            )
        )

    mitigations = (
        metadata.get(
            "potential_mitigations",
            [],
        )
    )

    if mitigations:
        parts.append(
            "Potential Mitigations:\n- "
            + "\n- ".join(
                mitigations
            )
        )

    related_cwes = (
        metadata.get(
            "related_cwes",
            [],
        )
    )

    if related_cwes:
        parts.append(
            "Related CWE IDs: "
            + ", ".join(
                related_cwes
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

    return "\n\n".join(
        parts
    )


def to_security_document(
    record:
        SecurityKnowledgeRecord,
) -> SecurityDocument:

    return SecurityDocument(
        id=(
            "mitre_cwe:"
            f"{record.source_id}"
        ),

        title=(
            f"{record.source_id} "
            f"{record.title}"
        ),

        content=build_cwe_content(
            record
        ),

        source="MITRE CWE",

        category="weakness",

        metadata={
            "source_id":
                record.source_id,

            "cwe_ids":
                record.cwe_ids,

            "source_url":
                record.source_url,

            **(
                record.metadata
                or {}
            ),
        },
    )


def build_cwe_rag_documents(
    input_path: Path = (
        CWE_PROCESSED_PATH
    ),
) -> list[
    SecurityDocument
]:
    records = load_cwe_records(
        input_path
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
        CWE_RAG_PATH
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
        build_cwe_rag_documents()
    )

    output_path = (
        save_rag_documents(
            documents
        )
    )

    print()
    print("=" * 60)
    print(
        "MITRE CWE RAG Adapter"
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