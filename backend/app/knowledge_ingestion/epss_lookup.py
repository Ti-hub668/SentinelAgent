import json
from pathlib import Path

from app.knowledge_ingestion.schema import (
    EPSSRecord,
)


EPSS_PROCESSED_DIR = Path(
    "knowledge/processed/epss"
)


class EPSSLookup:
    """
    Exact local lookup for normalized
    FIRST EPSS records.

    This class never calls the network.
    """

    def __init__(
        self,
        data_dir: Path = (
            EPSS_PROCESSED_DIR
        ),
    ) -> None:
        self.data_dir = data_dir

    @staticmethod
    def _normalize_cve_id(
        cve_id: str,
    ) -> str:
        return (
            cve_id
            .strip()
            .upper()
        )

    def get(
        self,
        cve_id: str,
    ) -> EPSSRecord | None:
        cve_id = (
            self._normalize_cve_id(
                cve_id
            )
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
            data = json.load(
                file
            )

        return EPSSRecord(
            **data
        )

    def exists(
        self,
        cve_id: str,
    ) -> bool:
        return (
            self.get(cve_id)
            is not None
        )


def main() -> None:
    lookup = EPSSLookup()

    test_cve = (
        "CVE-2021-44228"
    )

    record = lookup.get(
        test_cve
    )

    print()
    print("=" * 60)
    print(
        "FIRST EPSS Local Lookup"
    )
    print("=" * 60)

    if record is None:
        print(
            f"{test_cve}: "
            "NOT FOUND"
        )

        print(
            "Download and normalize "
            "the record first."
        )

        return

    print(
        f"CVE        : "
        f"{record.cve_id}"
    )

    print(
        f"EPSS       : "
        f"{record.epss_score}"
    )

    print(
        f"Percentile : "
        f"{record.percentile}"
    )

    print(
        f"Date       : "
        f"{record.score_date}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()