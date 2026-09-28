import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


EPSS_API_URL = (
    "https://api.first.org/data/v1/epss"
)

OUTPUT_DIR = Path(
    "knowledge/official/epss"
)

CVE_PATTERN = re.compile(
    r"^CVE-\d{4}-\d{4,}$",
    re.IGNORECASE,
)


def validate_cve_id(
    cve_id: str,
) -> str:
    normalized = (
        cve_id
        .strip()
        .upper()
    )

    if not CVE_PATTERN.match(
        normalized
    ):
        raise ValueError(
            f"Invalid CVE ID: {cve_id}"
        )

    return normalized


def download_epss(
    cve_id: str,
    timeout: float = 30.0,
) -> dict:
    """
    Download the latest FIRST EPSS score
    for one CVE.
    """

    cve_id = validate_cve_id(
        cve_id
    )

    query = urllib.parse.urlencode(
        {
            "cve": cve_id,
        }
    )

    url = (
        f"{EPSS_API_URL}?{query}"
    )

    request = (
        urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    "SentinelAgent/0.1",

                "Accept":
                    "application/json",
            },
        )
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        return json.load(
            response
        )


def save_epss(
    cve_id: str,
    data: dict,
) -> Path:
    """
    Save the raw FIRST EPSS response.
    """

    cve_id = validate_cve_id(
        cve_id
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / f"{cve_id}.json"
    )

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


def inspect_epss(
    data: dict,
) -> None:
    records = data.get(
        "data",
        [],
    )

    print()
    print("=" * 60)
    print(
        "FIRST EPSS Download Summary"
    )
    print("=" * 60)

    print(
        f"Status : "
        f"{data.get('status')}"
    )

    print(
        f"Total  : "
        f"{data.get('total')}"
    )

    if not records:
        print(
            "No EPSS record returned."
        )

        print("=" * 60)
        return

    record = records[0]

    print(
        f"CVE        : "
        f"{record.get('cve')}"
    )

    print(
        f"EPSS       : "
        f"{record.get('epss')}"
    )

    print(
        f"Percentile : "
        f"{record.get('percentile')}"
    )

    print(
        "Date       : "
        f"{record.get('date')}"
    )

    print("=" * 60)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python -m "
            "app.knowledge_ingestion.epss "
            "CVE-YYYY-NNNN"
        )

        raise SystemExit(1)

    cve_id = validate_cve_id(
        sys.argv[1]
    )

    print(
        f"Downloading EPSS for "
        f"{cve_id}..."
    )

    data = download_epss(
        cve_id
    )

    inspect_epss(
        data
    )

    path = save_epss(
        cve_id,
        data,
    )

    print(
        f"Saved: {path}"
    )


if __name__ == "__main__":
    main()