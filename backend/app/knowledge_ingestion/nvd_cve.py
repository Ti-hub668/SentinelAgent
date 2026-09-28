import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

OUTPUT_DIR = Path(
    "knowledge/official/nvd"
)

CVE_PATTERN = re.compile(
    r"^CVE-\d{4}-\d{4,}$",
    re.IGNORECASE,
)


def validate_cve_id(cve_id: str) -> str:
    normalized = cve_id.strip().upper()

    if not CVE_PATTERN.match(normalized):
        raise ValueError(
            f"Invalid CVE ID: {cve_id}"
        )

    return normalized


def download_cve(
    cve_id: str,
    timeout: float = 30.0,
) -> dict:
    cve_id = validate_cve_id(cve_id)

    query = urllib.parse.urlencode(
        {
            "cveId": cve_id,
        }
    )

    url = f"{NVD_API_URL}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SentinelAgent/0.1",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        return json.load(response)


def save_cve(
    cve_id: str,
    data: dict,
) -> Path:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR / f"{cve_id}.json"
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


def inspect_cve(
    data: dict,
) -> None:
    vulnerabilities = data.get(
        "vulnerabilities",
        []
    )

    print(
        f"Results: {len(vulnerabilities)}"
    )

    if not vulnerabilities:
        return

    cve = vulnerabilities[0].get(
        "cve",
        {}
    )

    print(
        f"CVE ID: {cve.get('id')}"
    )
    print(
        f"Published: {cve.get('published')}"
    )
    print(
        f"Modified: {cve.get('lastModified')}"
    )
    print(
        f"Status: {cve.get('vulnStatus')}"
    )

    descriptions = cve.get(
        "descriptions",
        []
    )

    english_description = next(
        (
            item.get("value")
            for item in descriptions
            if item.get("lang") == "en"
        ),
        None,
    )

    print(
        f"Description: {english_description}"
    )


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python -m "
            "app.knowledge_ingestion.nvd_cve "
            "CVE-YYYY-NNNN"
        )
        raise SystemExit(1)

    cve_id = validate_cve_id(
        sys.argv[1]
    )

    print(
        f"Downloading {cve_id} from NVD..."
    )

    data = download_cve(
        cve_id
    )

    inspect_cve(
        data
    )

    path = save_cve(
        cve_id,
        data,
    )

    print(
        f"Saved: {path}"
    )


if __name__ == "__main__":
    main()