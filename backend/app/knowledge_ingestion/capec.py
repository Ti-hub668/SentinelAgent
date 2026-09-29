import sys
import urllib.request
from pathlib import Path


CAPEC_OUTPUT_DIR = Path(
    "knowledge/official/mitre/capec"
)

CAPEC_XML_PATH = (
    CAPEC_OUTPUT_DIR
    / "capec_latest.xml"
)

CAPEC_XML_URL = (
    "https://capec.mitre.org/"
    "data/xml/capec_latest.xml"
)


def download_capec(
    timeout: float = 60.0,
) -> Path:
    """
    Download the latest official MITRE CAPEC XML catalog.
    """

    CAPEC_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = urllib.request.Request(
        CAPEC_XML_URL,
        headers={
            "User-Agent":
                "SentinelAgent/0.1",

            "Accept":
                "application/xml,"
                "text/xml,"
                "*/*",
        },
    )

    print(
        "Downloading MITRE CAPEC..."
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        data = response.read()

    CAPEC_XML_PATH.write_bytes(
        data
    )

    print(
        f"Saved XML: "
        f"{CAPEC_XML_PATH}"
    )

    return CAPEC_XML_PATH


def main() -> None:
    timeout = 60.0

    if len(sys.argv) > 1:
        timeout = float(
            sys.argv[1]
        )

    path = download_capec(
        timeout=timeout,
    )

    print()
    print("=" * 60)
    print(
        "MITRE CAPEC Download Complete"
    )
    print("=" * 60)

    print(
        f"XML : {path}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()