import json
from pathlib import Path

from app.knowledge_ingestion.schema import (
    SecurityKnowledgeRecord,
)

from app.rag.document import (
    SecurityDocument,
)


ATTACK_PROCESSED_PATH = Path(
    "knowledge/processed/"
    "mitre_attack.json"
)

ATTACK_RAG_PATH = Path(
    "knowledge/raw/"
    "mitre_attack.json"
)


def load_attack_records(
    path: Path = (
        ATTACK_PROCESSED_PATH
    ),
) -> list[
    SecurityKnowledgeRecord
]:

    if not path.exists():
        raise FileNotFoundError(
            "Normalized ATT&CK dataset "
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
            "ATT&CK normalized root "
            "must be a list."
        )

    return [
        SecurityKnowledgeRecord(
            **item
        )
        for item in data
    ]


def build_attack_content(
    record:
        SecurityKnowledgeRecord,
) -> str:

    metadata = (
        record.metadata
        or {}
    )

    parts = [
        (
            "ATT&CK Technique ID: "
            f"{record.source_id}"
        ),

        (
            "Technique Name: "
            f"{record.title}"
        ),

        (
            "Description: "
            f"{record.description}"
        ),
    ]

    technique_type = (
        metadata.get(
            "technique_type"
        )
    )

    if technique_type:
        parts.append(
            "Technique Type: "
            f"{technique_type}"
        )

    tactics = (
        metadata.get(
            "tactics",
            [],
        )
    )

    if tactics:
        parts.append(
            "ATT&CK Tactics: "
            + ", ".join(
                tactics
            )
        )

    platforms = (
        metadata.get(
            "platforms",
            [],
        )
    )

    if platforms:
        parts.append(
            "Platforms: "
            + ", ".join(
                platforms
            )
        )

    permissions = (
        metadata.get(
            "permissions_required",
            [],
        )
    )

    if permissions:
        parts.append(
            "Permissions Required: "
            + ", ".join(
                permissions
            )
        )

    requirements = (
        metadata.get(
            "system_requirements",
            [],
        )
    )

    if requirements:
        parts.append(
            "System Requirements:\n- "
            + "\n- ".join(
                requirements
            )
        )

    bypassed = (
        metadata.get(
            "defenses_bypassed",
            [],
        )
    )

    if bypassed:
        parts.append(
            "Defenses Bypassed: "
            + ", ".join(
                bypassed
            )
        )

    detection = (
        metadata.get(
            "detection"
        )
    )

    if detection:
        parts.append(
            "Detection Guidance: "
            f"{detection}"
        )

    data_sources = (
        metadata.get(
            "data_sources",
            [],
        )
    )

    if data_sources:
        parts.append(
            "Data Sources:\n- "
            + "\n- ".join(
                data_sources
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
            "mitre_attack:"
            f"{record.source_id}"
        ),

        title=(
            f"{record.source_id} "
            f"{record.title}"
        ),

        content=(
            build_attack_content(
                record
            )
        ),

        source=(
            "MITRE ATT&CK"
        ),

        category=(
            "attack_technique"
        ),

        metadata={
            "source_id":
                record.source_id,

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


def build_attack_rag_documents(
    input_path: Path = (
        ATTACK_PROCESSED_PATH
    ),
) -> list[
    SecurityDocument
]:

    records = (
        load_attack_records(
            input_path
        )
    )

    documents = []

    for record in records:

        metadata = (
            record.metadata
            or {}
        )

        if metadata.get(
            "deprecated"
        ):
            continue

        if metadata.get(
            "revoked"
        ):
            continue

        documents.append(
            to_security_document(
                record
            )
        )

    return documents


def save_rag_documents(
    documents: list[
        SecurityDocument
    ],

    output_path: Path = (
        ATTACK_RAG_PATH
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

    records = (
        load_attack_records()
    )

    documents = (
        build_attack_rag_documents()
    )

    filtered = (
        len(records)
        - len(documents)
    )

    output_path = (
        save_rag_documents(
            documents
        )
    )

    print()
    print("=" * 60)
    print(
        "MITRE ATT&CK RAG Adapter"
    )
    print("=" * 60)

    print(
        f"Loaded records : "
        f"{len(records)}"
    )

    print(
        f"Filtered       : "
        f"{filtered}"
    )

    print(
        f"RAG documents  : "
        f"{len(documents)}"
    )

    print(
        f"Saved          : "
        f"{output_path}"
    )

    if documents:
        print()
        print(
            f"First ID       : "
            f"{documents[0].id}"
        )

        print(
            f"Title          : "
            f"{documents[0].title}"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()