import json

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path

from app.knowledge_ingestion.schema import (
    SecurityKnowledgeRecord,
)


ATTACK_JSON_PATH = Path(
    "knowledge/official/mitre/attack/"
    "enterprise_attack.json"
)

ATTACK_PROCESSED_PATH = Path(
    "knowledge/processed/mitre_attack.json"
)


def unique(
    values: list[str],
) -> list[str]:

    return list(
        dict.fromkeys(
            value
            for value in values
            if value
        )
    )


def get_attack_external_id(
    item: dict,
) -> str | None:
    """
    Extract MITRE ATT&CK external ID,
    such as T1059 or T1059.003.
    """

    for reference in item.get(
        "external_references",
        [],
    ):
        if (
            reference.get(
                "source_name"
            )
            == "mitre-attack"
        ):
            external_id = (
                reference.get(
                    "external_id"
                )
            )

            if external_id:
                return (
                    str(external_id)
                    .strip()
                    .upper()
                )

    return None


def get_attack_url(
    item: dict,
) -> str | None:

    for reference in item.get(
        "external_references",
        [],
    ):
        if (
            reference.get(
                "source_name"
            )
            == "mitre-attack"
        ):
            url = reference.get(
                "url"
            )

            if url:
                return str(
                    url
                )

    return None


def get_references(
    item: dict,
) -> list[str]:

    results = []

    for reference in item.get(
        "external_references",
        [],
    ):
        url = reference.get(
            "url"
        )

        if url:
            results.append(
                str(url)
            )

    return unique(
        results
    )


def get_tactics(
    item: dict,
) -> list[str]:

    results = []

    for phase in item.get(
        "kill_chain_phases",
        [],
    ):
        phase_name = phase.get(
            "phase_name"
        )

        if phase_name:
            results.append(
                str(
                    phase_name
                )
            )

    return unique(
        results
    )


def normalize_attack_technique(
    item: dict,
    *,
    retrieved_at: str,
) -> SecurityKnowledgeRecord | None:

    attack_id = (
        get_attack_external_id(
            item
        )
    )

    if not attack_id:
        return None

    name = (
        str(
            item.get(
                "name",
                attack_id,
            )
        )
        .strip()
    )

    description = (
        str(
            item.get(
                "description",
                "",
            )
        )
        .strip()
    )

    platforms = [
        str(value)
        for value in item.get(
            "x_mitre_platforms",
            [],
        )
        if value
    ]

    tactics = get_tactics(
        item
    )

    data_sources = [
        str(value)
        for value in item.get(
            "x_mitre_data_sources",
            [],
        )
        if value
    ]

    permissions_required = [
        str(value)
        for value in item.get(
            "x_mitre_permissions_required",
            [],
        )
        if value
    ]

    system_requirements = [
        str(value)
        for value in item.get(
            "x_mitre_system_requirements",
            [],
        )
        if value
    ]

    defenses_bypassed = [
        str(value)
        for value in item.get(
            "x_mitre_defense_bypassed",
            [],
        )
        if value
    ]

    detection = (
        str(
            item.get(
                "x_mitre_detection",
                "",
            )
        )
        .strip()
    )

    references = (
        get_references(
            item
        )
    )

    source_url = (
        get_attack_url(
            item
        )
    )

    is_subtechnique = bool(
        item.get(
            "x_mitre_is_subtechnique",
            False,
        )
    )

    technique_type = (
        "sub-technique"
        if is_subtechnique
        else "technique"
    )

    tags = [
        "mitre",
        "attack",
        "enterprise",
        technique_type,
    ]

    tags.extend(
        tactic.lower()
        for tactic in tactics
    )

    return SecurityKnowledgeRecord(
        id=(
            "mitre_attack:"
            f"{attack_id}"
        ),

        source="mitre_attack",

        source_id=attack_id,

        knowledge_type=(
            "attack_technique"
        ),

        title=name,

        description=(
            description
            or name
        ),

        attack_ids=[
            attack_id
        ],

        affected_products=
            platforms,

        source_url=
            source_url,

        published_at=
            item.get(
                "created"
            ),

        modified_at=
            item.get(
                "modified"
            ),

        retrieved_at=
            retrieved_at,

        tags=tags,

        metadata={
            "stix_id":
                item.get(
                    "id"
                ),

            "is_subtechnique":
                is_subtechnique,

            "technique_type":
                technique_type,

            "tactics":
                tactics,

            "platforms":
                platforms,

            "data_sources":
                data_sources,

            "permissions_required":
                permissions_required,

            "system_requirements":
                system_requirements,

            "defenses_bypassed":
                defenses_bypassed,

            "detection":
                detection or None,

            "references":
                references,

            "version":
                item.get(
                    "x_mitre_version"
                ),

            "contributors":
                item.get(
                    "x_mitre_contributors",
                    [],
                ),

            "revoked":
                bool(
                    item.get(
                        "revoked",
                        False,
                    )
                ),

            "deprecated":
                bool(
                    item.get(
                        "x_mitre_deprecated",
                        False,
                    )
                ),
        },
    )


def normalize_attack_catalog(
    path: Path = (
        ATTACK_JSON_PATH
    ),
) -> list[
    SecurityKnowledgeRecord
]:

    if not path.exists():
        raise FileNotFoundError(
            "MITRE ATT&CK dataset "
            f"not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(
            file
        )

    objects = data.get(
        "objects",
        []
    )

    retrieved_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    records = []

    for item in objects:
        if (
            item.get(
                "type"
            )
            != "attack-pattern"
        ):
            continue

        record = (
            normalize_attack_technique(
                item,
                retrieved_at=
                    retrieved_at,
            )
        )

        if record is not None:
            records.append(
                record
            )

    return records


def save_records(
    records: list[
        SecurityKnowledgeRecord
    ],

    output_path: Path = (
        ATTACK_PROCESSED_PATH
    ),
) -> Path:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = [
        record.model_dump()
        for record in records
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
        normalize_attack_catalog()
    )

    output_path = (
        save_records(
            records
        )
    )

    active = [
        record
        for record in records
        if not (
            record.metadata.get(
                "deprecated"
            )
            or record.metadata.get(
                "revoked"
            )
        )
    ]

    deprecated = [
        record
        for record in records
        if record.metadata.get(
            "deprecated"
        )
    ]

    revoked = [
        record
        for record in records
        if record.metadata.get(
            "revoked"
        )
    ]

    subtechniques = [
        record
        for record in active
        if record.metadata.get(
            "is_subtechnique"
        )
    ]

    print()
    print("=" * 60)
    print(
        "MITRE ATT&CK Normalization"
    )
    print("=" * 60)

    print(
        f"All records     : "
        f"{len(records)}"
    )

    print(
        f"Active records  : "
        f"{len(active)}"
    )

    print(
        f"Deprecated      : "
        f"{len(deprecated)}"
    )

    print(
        f"Revoked         : "
        f"{len(revoked)}"
    )

    print(
        f"Sub-techniques  : "
        f"{len(subtechniques)}"
    )

    print(
        f"Saved           : "
        f"{output_path}"
    )

    if records:
        print()
        print(
            f"First ID        : "
            f"{records[0].source_id}"
        )

        print(
            f"Title           : "
            f"{records[0].title}"
        )

        print(
            "Tactics         : "
            f"{records[0].metadata.get('tactics')}"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()