import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


CISA_KEV_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/"
    "known_exploited_vulnerabilities.json"
)

OUTPUT_PATH = Path(
    "knowledge/official/cisa/"
    "known_exploited_vulnerabilities.json"
)


def download_kev() -> dict:
    """
    Download the official CISA Known Exploited
    Vulnerabilities catalog.
    """

    print("Downloading CISA KEV...")
    print(f"Source: {CISA_KEV_URL}")

    request = Request(
        CISA_KEV_URL,
        headers={
            "User-Agent": "SentinelAgent/0.1"
        },
    )

    with urlopen(
        request,
        timeout=30,
    ) as response:
        data = json.load(response)

    return data


def save_kev(data: dict) -> None:
    """
    Save the original CISA KEV JSON locally.
    """

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Saved to: {OUTPUT_PATH}")


def inspect_kev(data: dict) -> None:
    """
    Print basic metadata without modifying
    the original source data.
    """

    vulnerabilities = data.get(
        "vulnerabilities",
        [],
    )

    print()
    print("=" * 60)
    print("CISA KEV Download Summary")
    print("=" * 60)

    print(
        f"Catalog title : "
        f"{data.get('title')}"
    )

    print(
        f"Catalog version: "
        f"{data.get('catalogVersion')}"
    )

    print(
        f"Date released : "
        f"{data.get('dateReleased')}"
    )

    print(
        f"Vulnerabilities: "
        f"{len(vulnerabilities)}"
    )

    print(
        "Retrieved at  : "
        f"{datetime.now(timezone.utc).isoformat()}"
    )

    if vulnerabilities:
        first = vulnerabilities[0]

        print()
        print("First vulnerability:")
        print(
            json.dumps(
                first,
                ensure_ascii=False,
                indent=2,
            )
        )

    print("=" * 60)


def main() -> None:
    data = download_kev()

    save_kev(data)

    inspect_kev(data)


if __name__ == "__main__":
    main()