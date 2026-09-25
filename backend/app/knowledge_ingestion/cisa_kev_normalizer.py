import json
from datetime import datetime, timezone
from pathlib import Path

from app.knowledge_ingestion.schema import SecurityKnowledgeRecord


INPUT_PATH = Path(
    "knowledge/official/cisa/"
    "known_exploited_vulnerabilities.json"
)

OUTPUT_PATH = Path(
    "knowledge/processed/cisa_kev.json"
)


def load_kev() -> dict:
    with INPUT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def normalize_kev_record(
    item: dict,
    retrieved_at: str,
) -> SecurityKnowledgeRecord:
    """
    Convert one raw CISA KEV entry into the
    SentinelAgent unified security knowledge schema.
    """

    cve_id = item["cveID"]

    vendor = item.get(
        "vendorProject",
        "",
    )

    product = item.get(
        "product",
        "",
    )

    affected_products = []

    if vendor or product:
        affected_products.append(
            " ".join(
                part
                for part in [vendor, product]
                if part
            )
        )

    return SecurityKnowledgeRecord(
        id=f"cisa_kev:{cve_id}",
        source="cisa_kev",
        source_id=cve_id,
        knowledge_type=(
            "known_exploited_vulnerability"
        ),
        title=item.get(
            "vulnerabilityName",
            cve_id,
        ),
        description=item.get(
            "shortDescription",
            "",
        ),
        remediation=item.get(
            "requiredAction"
        ),
        cwe_ids=item.get(
            "cwes",
            [],
        ),
        cve_ids=[cve_id],
        known_exploited=True,
        affected_products=affected_products,
        source_url=(
            "https://www.cisa.gov/"
            "known-exploited-vulnerabilities-catalog"
        ),
        published_at=item.get(
            "dateAdded"
        ),
        retrieved_at=retrieved_at,
        tags=[
            "cisa-kev",
            "known-exploited",
        ],
        metadata={
            "vendor_project": vendor,
            "product": product,
            "date_added": item.get(
                "dateAdded"
            ),
            "due_date": item.get(
                "dueDate"
            ),
            "known_ransomware_campaign_use": (
                item.get(
                    "knownRansomwareCampaignUse"
                )
            ),
            "forensic_triage": item.get(
                "forensicTriage"
            ),
            "notes": item.get(
                "notes"
            ),
        },
    )


def normalize_catalog(
    data: dict,
) -> list[SecurityKnowledgeRecord]:
    retrieved_at = (
        datetime.now(timezone.utc).isoformat()
    )

    records = []

    for item in data.get(
        "vulnerabilities",
        [],
    ):
        record = normalize_kev_record(
            item,
            retrieved_at,
        )

        records.append(record)

    return records


def save_records(
    records: list[SecurityKnowledgeRecord],
) -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_data = [
        record.model_dump()
        for record in records
    ]

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output_data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def inspect_records(
    records: list[SecurityKnowledgeRecord],
) -> None:
    print()
    print("=" * 60)
    print("CISA KEV Normalization Summary")
    print("=" * 60)

    print(
        f"Normalized records: "
        f"{len(records)}"
    )

    if records:
        print()
        print("First normalized record:")

        print(
            records[0].model_dump_json(
                indent=2
            )
        )

    print("=" * 60)


def main() -> None:
    data = load_kev()

    records = normalize_catalog(data)

    save_records(records)

    inspect_records(records)


if __name__ == "__main__":
    main()