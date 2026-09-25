import json
from pathlib import Path

from app.knowledge_ingestion.schema import (
    SecurityKnowledgeRecord,
)


NVD_PROCESSED_DIR = Path(
    "knowledge/processed/nvd"
)


class NVDLookup:
    """
    Exact local lookup for normalized NVD CVE records.

    This class does not call the NVD API.
    It only reads CVE records already downloaded
    and normalized into knowledge/processed/nvd/.
    """

    def __init__(
        self,
        data_dir: Path = NVD_PROCESSED_DIR,
    ) -> None:
        self.data_dir = data_dir

    @staticmethod
    def _normalize_cve_id(
        cve_id: str,
    ) -> str:
        return cve_id.strip().upper()

    def get(
        self,
        cve_id: str,
    ) -> SecurityKnowledgeRecord | None:
        cve_id = self._normalize_cve_id(
            cve_id
        )

        path = (
            self.data_dir
            / f"{cve_id}.json"
        )

        if not path.exists():
            return None

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return SecurityKnowledgeRecord(
            **data
        )

    def exists(
        self,
        cve_id: str,
    ) -> bool:
        return self.get(cve_id) is not None


def main():
    lookup = NVDLookup()

    test_cve = "CVE-2026-15144"

    record = lookup.get(
        test_cve
    )

    print()
    print("NVD Local Lookup")
    print("=" * 60)

    if record is None:
        print(
            f"{test_cve}: NOT FOUND"
        )
        return

    print(
        f"CVE       : {record.source_id}"
    )
    print(
        f"Description: {record.description}"
    )
    print(
        f"CVSS      : {record.cvss_score}"
    )
    print(
        f"Severity  : {record.severity}"
    )
    print(
        f"CWE       : {record.cwe_ids}"
    )
    print(
        "Products  : "
        f"{len(record.affected_products)}"
    )

    print()
    print(
        "Unknown CVE test:"
    )
    print(
        lookup.exists(
            "CVE-2099-999999"
        )
    )


if __name__ == "__main__":
    main()