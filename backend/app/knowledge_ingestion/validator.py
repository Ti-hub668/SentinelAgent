import json
import re
from collections import Counter
from pathlib import Path

from app.knowledge_ingestion.schema import SecurityKnowledgeRecord


CISA_PROCESSED_PATH = Path(
    "knowledge/processed/cisa_kev.json"
)

CVE_PATTERN = re.compile(
    r"^CVE-\d{4}-\d{4,}$"
)

CWE_PATTERN = re.compile(
    r"^CWE-\d+$"
)


def load_records(
    path: Path,
) -> list[SecurityKnowledgeRecord]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_records = json.load(file)

    return [
        SecurityKnowledgeRecord(**item)
        for item in raw_records
    ]


def validate_cisa_kev(
    records: list[SecurityKnowledgeRecord],
) -> dict:
    issues = []

    source_ids = [
        record.source_id
        for record in records
    ]

    duplicate_ids = [
        source_id
        for source_id, count
        in Counter(source_ids).items()
        if count > 1
    ]

    for duplicate_id in duplicate_ids:
        issues.append(
            {
                "type": "duplicate_source_id",
                "record": duplicate_id,
            }
        )

    for record in records:
        if not record.source_id:
            issues.append(
                {
                    "type": "empty_source_id",
                    "record": record.id,
                }
            )

        elif not CVE_PATTERN.match(
            record.source_id
        ):
            issues.append(
                {
                    "type": "invalid_cve_id",
                    "record": record.source_id,
                }
            )

        if record.source != "cisa_kev":
            issues.append(
                {
                    "type": "invalid_source",
                    "record": record.id,
                }
            )

        if (
            record.knowledge_type
            != "known_exploited_vulnerability"
        ):
            issues.append(
                {
                    "type": "invalid_knowledge_type",
                    "record": record.id,
                }
            )

        if not record.known_exploited:
            issues.append(
                {
                    "type": "known_exploited_false",
                    "record": record.id,
                }
            )

        if record.cve_ids != [
            record.source_id
        ]:
            issues.append(
                {
                    "type": "cve_mapping_mismatch",
                    "record": record.id,
                }
            )

        if not record.title.strip():
            issues.append(
                {
                    "type": "empty_title",
                    "record": record.id,
                }
            )

        if not record.description.strip():
            issues.append(
                {
                    "type": "empty_description",
                    "record": record.id,
                }
            )

        for cwe_id in record.cwe_ids:
            if not CWE_PATTERN.match(cwe_id):
                issues.append(
                    {
                        "type": "invalid_cwe_id",
                        "record": record.id,
                        "value": cwe_id,
                    }
                )

    issue_counts = Counter(
        issue["type"]
        for issue in issues
    )

    return {
        "total_records": len(records),
        "unique_source_ids": len(
            set(source_ids)
        ),
        "issues": issues,
        "issue_counts": dict(
            issue_counts
        ),
    }


def print_report(
    report: dict,
) -> None:
    print()
    print("=" * 60)
    print("SentinelAgent Official Knowledge Validator")
    print("=" * 60)

    print(
        f"Records           : "
        f"{report['total_records']}"
    )

    print(
        f"Unique source IDs : "
        f"{report['unique_source_ids']}"
    )

    print(
        f"Total issues      : "
        f"{len(report['issues'])}"
    )

    print()

    if report["issue_counts"]:
        print("Issue Types")
        print("-" * 60)

        for issue_type, count in sorted(
            report["issue_counts"].items()
        ):
            print(
                f"{issue_type:30} "
                f"{count}"
            )

        print()
        print("First 10 Issues")
        print("-" * 60)

        for issue in report["issues"][:10]:
            print(issue)

    else:
        print(
            "Validation result  : PASS"
        )
        print(
            "No data quality issues detected."
        )

    print("=" * 60)


def main() -> None:
    records = load_records(
        CISA_PROCESSED_PATH
    )

    report = validate_cisa_kev(
        records
    )

    print_report(report)


if __name__ == "__main__":
    main()