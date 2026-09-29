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


CWE_XML_PATH = Path(
    "knowledge/official/mitre/cwe/"
    "cwec_latest.xml"
)

CWE_PROCESSED_PATH = Path(
    "knowledge/processed/cwe.json"
)


def local_name(
    tag: str,
) -> str:
    """
    Remove an XML namespace from one element tag.
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
    """
    Extract normalized mixed text from an XML element.
    """

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


def parse_mitigations(
    weakness: ET.Element,
) -> list[str]:
    container = direct_child(
        weakness,
        "Potential_Mitigations",
    )

    if container is None:
        return []

    results = []

    for mitigation in direct_children(
        container,
        "Mitigation",
    ):
        descriptions = [
            element_text(item)
            for item in direct_children(
                mitigation,
                "Description",
            )
        ]

        descriptions = [
            item
            for item in descriptions
            if item
        ]

        if descriptions:
            results.append(
                " ".join(
                    descriptions
                )
            )

    return list(
        dict.fromkeys(
            results
        )
    )


def parse_consequences(
    weakness: ET.Element,
) -> list[str]:
    container = direct_child(
        weakness,
        "Common_Consequences",
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
                + ", ".join(scopes)
            )

        if impacts:
            parts.append(
                "Impact: "
                + ", ".join(impacts)
            )

        if notes:
            parts.append(
                "Note: "
                + " ".join(notes)
            )

        if parts:
            results.append(
                "; ".join(parts)
            )

    return list(
        dict.fromkeys(
            results
        )
    )


def parse_related_capec(
    weakness: ET.Element,
) -> list[str]:
    results = []

    for item in descendants(
        weakness,
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

    return list(
        dict.fromkeys(
            results
        )
    )


def parse_related_cwes(
    weakness: ET.Element,
) -> list[str]:
    results = []

    for item in descendants(
        weakness,
        "Related_Weakness",
    ):
        related_id = (
            item.attrib.get(
                "CWE_ID"
            )
        )

        if related_id:
            results.append(
                f"CWE-{related_id}"
            )

    return list(
        dict.fromkeys(
            results
        )
    )


def normalize_weakness(
    weakness: ET.Element,
    *,
    catalog_version: str | None,
    catalog_date: str | None,
    retrieved_at: str,
) -> SecurityKnowledgeRecord:
    weakness_id = (
        weakness.attrib.get(
            "ID",
            "",
        )
        .strip()
    )

    if not weakness_id:
        raise ValueError(
            "CWE Weakness has no ID."
        )

    cwe_id = (
        f"CWE-{weakness_id}"
    )

    name = (
        weakness.attrib.get(
            "Name",
            cwe_id,
        )
        .strip()
    )

    description = element_text(
        direct_child(
            weakness,
            "Description",
        )
    )

    extended_description = (
        element_text(
            direct_child(
                weakness,
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

    mitigations = (
        parse_mitigations(
            weakness
        )
    )

    consequences = (
        parse_consequences(
            weakness
        )
    )

    related_capec = (
        parse_related_capec(
            weakness
        )
    )

    related_cwes = (
        parse_related_cwes(
            weakness
        )
    )

    likelihood = element_text(
        direct_child(
            weakness,
            "Likelihood_Of_Exploit",
        )
    )

    abstraction = (
        weakness.attrib.get(
            "Abstraction"
        )
    )

    structure = (
        weakness.attrib.get(
            "Structure"
        )
    )

    status = (
        weakness.attrib.get(
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
        "cwe",
        "weakness",
    ]

    if abstraction:
        tags.append(
            abstraction.lower()
        )

    return SecurityKnowledgeRecord(
        id=f"cwe:{cwe_id}",
        source="cwe",
        source_id=cwe_id,
        knowledge_type="weakness",
        title=name,
        description=(
            final_description
            or name
        ),
        remediation=remediation,
        cwe_ids=[
            cwe_id,
        ],
        source_url=(
            "https://"
            "cwe.mitre.org/data/"
            f"definitions/{weakness_id}.html"
        ),
        retrieved_at=retrieved_at,
        tags=tags,
        metadata={
            "abstraction":
                abstraction,

            "structure":
                structure,

            "status":
                status,

            "likelihood_of_exploit":
                likelihood or None,

            "common_consequences":
                consequences,

            "potential_mitigations":
                mitigations,

            "related_cwes":
                related_cwes,

            "related_capec":
                related_capec,

            "catalog_version":
                catalog_version,

            "catalog_date":
                catalog_date,
        },
    )


def normalize_cwe_catalog(
    xml_path: Path = CWE_XML_PATH,
) -> list[
    SecurityKnowledgeRecord
]:
    if not xml_path.exists():
        raise FileNotFoundError(
            "CWE XML not found: "
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
            != "Weakness"
        ):
            continue

        record = normalize_weakness(
            element,

            catalog_version=
                catalog_version,

            catalog_date=
                catalog_date,

            retrieved_at=
                retrieved_at,
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
        CWE_PROCESSED_PATH
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
        normalize_cwe_catalog()
    )

    output_path = (
        save_records(
            records
        )
    )

    print()
    print("=" * 60)
    print(
        "MITRE CWE Normalization"
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

    print("=" * 60)


if __name__ == "__main__":
    main()