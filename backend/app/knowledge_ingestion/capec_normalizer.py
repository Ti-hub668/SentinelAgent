import json
import xml.etree.ElementTree as ET

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path

from app.knowledge_ingestion.schema import (
    SecurityKnowledgeRecord,
)


CAPEC_XML_PATH = Path(
    "knowledge/official/mitre/capec/"
    "capec_latest.xml"
)

CAPEC_PROCESSED_PATH = Path(
    "knowledge/processed/capec.json"
)


def local_name(
    tag: str,
) -> str:
    """
    Remove XML namespace.
    """

    if "}" in tag:
        return tag.split(
            "}",
            1,
        )[1]

    return tag


def clean_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    return " ".join(
        value.split()
    )


def element_text(
    element: ET.Element | None,
) -> str:
    if element is None:
        return ""

    return clean_text(
        " ".join(
            element.itertext()
        )
    )


def direct_child(
    element: ET.Element,
    name: str,
) -> ET.Element | None:

    for child in element:
        if (
            local_name(
                child.tag
            )
            == name
        ):
            return child

    return None


def direct_children(
    element: ET.Element,
    name: str,
) -> list[ET.Element]:

    return [
        child
        for child in element
        if (
            local_name(
                child.tag
            )
            == name
        )
    ]


def descendants(
    element: ET.Element,
    name: str,
) -> list[ET.Element]:

    return [
        child
        for child in element.iter()
        if (
            local_name(
                child.tag
            )
            == name
        )
    ]


def unique(
    values: list[str],
) -> list[str]:

    return list(
        dict.fromkeys(
            item
            for item in values
            if item
        )
    )


def parse_related_cwes(
    attack_pattern: ET.Element,
) -> list[str]:

    results = []

    for item in descendants(
        attack_pattern,
        "Related_Weakness",
    ):
        cwe_id = (
            item.attrib.get(
                "CWE_ID"
            )
        )

        if cwe_id:
            results.append(
                f"CWE-{cwe_id}"
            )

    return unique(
        results
    )


def parse_related_capec(
    attack_pattern: ET.Element,
) -> list[str]:

    results = []

    for item in descendants(
        attack_pattern,
        "Related_Attack_Pattern",
    ):
        capec_id = (
            item.attrib.get(
                "CAPEC_ID"
            )
        )

        if capec_id:
            results.append(
                f"CAPEC-{capec_id}"
            )

    return unique(
        results
    )


def parse_prerequisites(
    attack_pattern: ET.Element,
) -> list[str]:

    container = direct_child(
        attack_pattern,
        "Prerequisites",
    )

    if container is None:
        return []

    results = []

    for item in direct_children(
        container,
        "Prerequisite",
    ):
        text = element_text(
            item
        )

        if text:
            results.append(
                text
            )

    return unique(
        results
    )


def parse_mitigations(
    attack_pattern: ET.Element,
) -> list[str]:

    container = direct_child(
        attack_pattern,
        "Mitigations",
    )

    if container is None:
        return []

    results = []

    for item in direct_children(
        container,
        "Mitigation",
    ):
        text = element_text(
            item
        )

        if text:
            results.append(
                text
            )

    return unique(
        results
    )


def parse_indicators(
    attack_pattern: ET.Element,
) -> list[str]:

    container = direct_child(
        attack_pattern,
        "Indicators",
    )

    if container is None:
        return []

    results = []

    for item in direct_children(
        container,
        "Indicator",
    ):
        text = element_text(
            item
        )

        if text:
            results.append(
                text
            )

    return unique(
        results
    )


def parse_consequences(
    attack_pattern: ET.Element,
) -> list[str]:

    container = direct_child(
        attack_pattern,
        "Consequences",
    )

    if container is None:
        return []

    results = []

    for consequence in direct_children(
        container,
        "Consequence",
    ):
        scopes = [
            element_text(item)
            for item in direct_children(
                consequence,
                "Scope",
            )
        ]

        impacts = [
            element_text(item)
            for item in direct_children(
                consequence,
                "Impact",
            )
        ]

        likelihood = element_text(
            direct_child(
                consequence,
                "Likelihood",
            )
        )

        notes = [
            element_text(item)
            for item in direct_children(
                consequence,
                "Note",
            )
        ]

        parts = []

        scopes = [
            item
            for item in scopes
            if item
        ]

        impacts = [
            item
            for item in impacts
            if item
        ]

        notes = [
            item
            for item in notes
            if item
        ]

        if scopes:
            parts.append(
                "Scope: "
                + ", ".join(
                    scopes
                )
            )

        if impacts:
            parts.append(
                "Impact: "
                + ", ".join(
                    impacts
                )
            )

        if likelihood:
            parts.append(
                "Likelihood: "
                + likelihood
            )

        if notes:
            parts.append(
                "Note: "
                + " ".join(
                    notes
                )
            )

        if parts:
            results.append(
                "; ".join(
                    parts
                )
            )

    return unique(
        results
    )


def parse_execution_flow(
    attack_pattern: ET.Element,
) -> list[str]:

    container = direct_child(
        attack_pattern,
        "Execution_Flow",
    )

    if container is None:
        return []

    results = []

    for step in descendants(
        container,
        "Attack_Step",
    ):
        step_number = element_text(
            direct_child(
                step,
                "Step",
            )
        )

        phase = element_text(
            direct_child(
                step,
                "Phase",
            )
        )

        description = element_text(
            direct_child(
                step,
                "Description",
            )
        )

        techniques = [
            element_text(item)
            for item in descendants(
                step,
                "Technique",
            )
        ]

        techniques = [
            item
            for item in techniques
            if item
        ]

        parts = []

        if step_number:
            parts.append(
                f"Step {step_number}"
            )

        if phase:
            parts.append(
                f"Phase: {phase}"
            )

        if description:
            parts.append(
                description
            )

        if techniques:
            parts.append(
                "Techniques: "
                + "; ".join(
                    techniques
                )
            )

        if parts:
            results.append(
                " | ".join(
                    parts
                )
            )

    return unique(
        results
    )


def parse_attack_mappings(
    attack_pattern: ET.Element,
) -> list[str]:
    """
    Extract ATT&CK technique IDs from CAPEC taxonomy mappings.

    CAPEC typically stores ATT&CK IDs without the leading T,
    for example 1499.002.
    """

    results = []

    for mapping in descendants(
        attack_pattern,
        "Taxonomy_Mapping",
    ):
        mapping_text = (
            element_text(
                mapping
            )
            .upper()
        )

        attributes_text = (
            " ".join(
                str(value)
                for value
                in mapping.attrib.values()
            )
            .upper()
        )

        if (
            "ATT&CK" not in mapping_text
            and "ATTACK" not in mapping_text
            and "ATT&CK" not in attributes_text
            and "ATTACK" not in attributes_text
        ):
            continue

        entry_id = element_text(
            direct_child(
                mapping,
                "Entry_ID",
            )
        )

        if not entry_id:
            entry_id = (
                mapping.attrib.get(
                    "Entry_ID"
                )
                or mapping.attrib.get(
                    "Entry_IDs"
                )
                or ""
            )

        entry_id = (
            str(entry_id)
            .strip()
            .upper()
        )

        if not entry_id:
            continue

        if not entry_id.startswith(
            "T"
        ):
            entry_id = (
                f"T{entry_id}"
            )

        results.append(
            entry_id
        )

    return unique(
        results
    )


def normalize_attack_pattern(
    attack_pattern: ET.Element,
    *,
    catalog_version: str | None,
    catalog_date: str | None,
    retrieved_at: str,
) -> SecurityKnowledgeRecord:

    raw_id = (
        attack_pattern.attrib
        .get(
            "ID",
            "",
        )
        .strip()
    )

    if not raw_id:
        raise ValueError(
            "CAPEC Attack Pattern "
            "has no ID."
        )

    capec_id = (
        f"CAPEC-{raw_id}"
    )

    title = (
        attack_pattern.attrib
        .get(
            "Name",
            capec_id,
        )
        .strip()
    )

    description = element_text(
        direct_child(
            attack_pattern,
            "Description",
        )
    )

    extended_description = (
        element_text(
            direct_child(
                attack_pattern,
                "Extended_Description",
            )
        )
    )

    description_parts = [
        item
        for item in [
            description,
            extended_description,
        ]
        if item
    ]

    final_description = (
        "\n\n".join(
            description_parts
        )
    )

    cwe_ids = (
        parse_related_cwes(
            attack_pattern
        )
    )

    related_capec = (
        parse_related_capec(
            attack_pattern
        )
    )

    prerequisites = (
        parse_prerequisites(
            attack_pattern
        )
    )

    execution_flow = (
        parse_execution_flow(
            attack_pattern
        )
    )

    consequences = (
        parse_consequences(
            attack_pattern
        )
    )

    mitigations = (
        parse_mitigations(
            attack_pattern
        )
    )

    indicators = (
        parse_indicators(
            attack_pattern
        )
    )

    attack_ids = (
        parse_attack_mappings(
            attack_pattern
        )
    )

    likelihood = element_text(
        direct_child(
            attack_pattern,
            "Likelihood_Of_Attack",
        )
    )

    severity = element_text(
        direct_child(
            attack_pattern,
            "Typical_Severity",
        )
    )

    abstraction = (
        attack_pattern.attrib.get(
            "Abstraction"
        )
    )

    status = (
        attack_pattern.attrib.get(
            "Status"
        )
    )

    remediation = None

    if mitigations:
        remediation = (
            "\n\n".join(
                mitigations
            )
        )

    tags = [
        "mitre",
        "capec",
        "attack-pattern",
    ]

    if abstraction:
        tags.append(
            abstraction.lower()
        )

    return SecurityKnowledgeRecord(
        id=(
            f"capec:{capec_id}"
        ),

        source="capec",

        source_id=capec_id,

        knowledge_type=(
            "attack_pattern"
        ),

        title=title,

        description=(
            final_description
            or title
        ),

        remediation=remediation,

        severity=(
            severity.lower()
            if severity
            else None
        ),

        cwe_ids=cwe_ids,

        attack_ids=attack_ids,

        source_url=(
            "https://capec.mitre.org/"
            "data/definitions/"
            f"{raw_id}.html"
        ),

        retrieved_at=
            retrieved_at,

        tags=tags,

        metadata={
            "abstraction":
                abstraction,

            "status":
                status,

            "likelihood_of_attack":
                likelihood or None,

            "typical_severity":
                severity or None,

            "prerequisites":
                prerequisites,

            "execution_flow":
                execution_flow,

            "consequences":
                consequences,

            "mitigations":
                mitigations,

            "indicators":
                indicators,

            "related_capec":
                related_capec,

            "attack_mappings":
                attack_ids,

            "catalog_version":
                catalog_version,

            "catalog_date":
                catalog_date,
        },
    )


def normalize_capec_catalog(
    xml_path: Path = (
        CAPEC_XML_PATH
    ),
) -> list[
    SecurityKnowledgeRecord
]:

    if not xml_path.exists():
        raise FileNotFoundError(
            "CAPEC XML not found: "
            f"{xml_path}"
        )

    tree = ET.parse(
        xml_path
    )

    root = tree.getroot()

    catalog_version = (
        root.attrib.get(
            "Version"
        )
    )

    catalog_date = (
        root.attrib.get(
            "Date"
        )
    )

    retrieved_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    records = []

    for element in root.iter():
        if (
            local_name(
                element.tag
            )
            != "Attack_Pattern"
        ):
            continue

        record = (
            normalize_attack_pattern(
                element,
                catalog_version=
                    catalog_version,
                catalog_date=
                    catalog_date,
                retrieved_at=
                    retrieved_at,
            )
        )

        records.append(
            record
        )

    return records


def save_records(
    records: list[
        SecurityKnowledgeRecord
    ],
    output_path: Path = (
        CAPEC_PROCESSED_PATH
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
        normalize_capec_catalog()
    )

    output_path = (
        save_records(
            records
        )
    )

    print()
    print("=" * 60)
    print(
        "MITRE CAPEC Normalization"
    )
    print("=" * 60)

    print(
        f"Records : "
        f"{len(records)}"
    )

    print(
        f"Saved   : "
        f"{output_path}"
    )

    if records:
        first = records[0]

        print()
        print(
            f"First   : "
            f"{first.source_id}"
        )

        print(
            f"Title   : "
            f"{first.title}"
        )

        print(
            f"CWE     : "
            f"{first.cwe_ids}"
        )

        print(
            f"ATT&CK  : "
            f"{first.attack_ids}"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()