import json
from pathlib import Path

from app.knowledge_ingestion.schema import SecurityKnowledgeRecord


KEV_PATH = Path(
    "knowledge/processed/cisa_kev.json"
)


class KEVLookup:
    """
    Local lookup service for normalized CISA KEV records.
    """

    def __init__(
        self,
        path: Path = KEV_PATH,
    ) -> None:
        self.path = path
        self._records: dict[
            str,
            SecurityKnowledgeRecord,
        ] = {}

        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(
                f"CISA KEV dataset not found: {self.path}"
            )

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        for item in data:
            record = SecurityKnowledgeRecord(
                **item
            )

            self._records[
                record.source_id.upper()
            ] = record

    def count(self) -> int:
        return len(self._records)

    def get(
        self,
        cve_id: str,
    ) -> SecurityKnowledgeRecord | None:
        normalized_id = (
            cve_id
            .strip()
            .upper()
        )

        return self._records.get(
            normalized_id
        )

    def is_known_exploited(
        self,
        cve_id: str,
    ) -> bool:
        record = self.get(cve_id)

        return (
            record is not None
            and record.known_exploited
        )


def main() -> None:
    lookup = KEVLookup()

    print()
    print("=" * 60)
    print("SentinelAgent CISA KEV Lookup")
    print("=" * 60)

    print(
        f"Loaded KEV records: "
        f"{lookup.count()}"
    )

    test_cve = "CVE-2026-7273"

    record = lookup.get(test_cve)

    print()
    print(f"Query: {test_cve}")

    if record is None:
        print("Known exploited: NO")

    else:
        print("Known exploited: YES")
        print(f"Title   : {record.title}")

        print(
            "Product : "
            f"{', '.join(record.affected_products)}"
        )

        print(
            "CWE     : "
            f"{', '.join(record.cwe_ids)}"
        )

        print(
            "Action  : "
            f"{record.remediation}"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()