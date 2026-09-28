import json
import sys
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from app.knowledge_ingestion.schema import (
    EPSSRecord,
)


RAW_DIR = Path(
    "knowledge/official/epss"
)

PROCESSED_DIR = Path(
    "knowledge/processed/epss"
)


def normalize_epss(
    data: dict,
) -> EPSSRecord:
    """
    Normalize one FIRST EPSS API response.
    """

    records = data.get(
        "data",
        [],
    )

    if not records:
        raise ValueError(
            "FIRST EPSS response "
            "contains no records."
        )

    item = records[0]

    cve_id = (
        str(
            item.get(
                "cve",
                "",
            )
        )
        .strip()
        .upper()
    )

    if not cve_id:
        raise ValueError(
            "EPSS record has no CVE ID."
        )

    epss_raw = item.get(
        "epss"
    )

    percentile_raw = item.get(
        "percentile"
    )

    if epss_raw is None:
        raise ValueError(
            "EPSS record has no score."
        )

    if percentile_raw is None:
        raise ValueError(
            "EPSS record has no percentile."
        )

    return EPSSRecord(
        cve_id=cve_id,

        epss_score=float(
            epss_raw
        ),

        percentile=float(
            percentile_raw
        ),

        score_date=(
            item.get("date")
            or item.get("created")
        ),

        retrieved_at=(
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
    )


def save_record(
    record: EPSSRecord,
) -> Path:
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        PROCESSED_DIR
        / f"{record.cve_id}.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            record.model_dump(),
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python -m "
            "app.knowledge_ingestion."
            "epss_normalizer "
            "CVE-YYYY-NNNN"
        )

        raise SystemExit(1)

    cve_id = (
        sys.argv[1]
        .strip()
        .upper()
    )

    input_path = (
        RAW_DIR
        / f"{cve_id}.json"
    )

    if not input_path.exists():
        raise FileNotFoundError(
            "EPSS raw file not found: "
            f"{input_path}"
        )

    with input_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(
            file
        )

    record = normalize_epss(
        data
    )

    output_path = save_record(
        record
    )

    print()
    print("=" * 60)
    print(
        "FIRST EPSS Normalization"
    )
    print("=" * 60)

    print(
        f"CVE        : "
        f"{record.cve_id}"
    )

    print(
        f"EPSS       : "
        f"{record.epss_score:.6f}"
    )

    print(
        f"Percentile : "
        f"{record.percentile:.6f}"
    )

    print(
        f"Date       : "
        f"{record.score_date}"
    )

    print(
        f"Saved      : "
        f"{output_path}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()