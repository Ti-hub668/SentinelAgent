import json
import sys
import urllib.request
from pathlib import Path


ATTACK_OUTPUT_DIR = Path(
    "knowledge/official/mitre/attack"
)

ATTACK_JSON_PATH = (
    ATTACK_OUTPUT_DIR
    / "enterprise_attack.json"
)

ATTACK_JSON_URL = (
    "https://raw.githubusercontent.com/"
    "mitre-attack/attack-stix-data/"
    "master/enterprise-attack/"
    "enterprise-attack.json"
)


def download_enterprise_attack(
    timeout: float = 120.0,
) -> Path:
    """
    Download the latest official MITRE
    Enterprise ATT&CK STIX 2.1 collection.
    """

    ATTACK_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = urllib.request.Request(
        ATTACK_JSON_URL,
        headers={
            "User-Agent":
                "SentinelAgent/0.1",
            "Accept":
                "application/json",
        },
    )

    print(
        "Downloading MITRE "
        "Enterprise ATT&CK..."
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        data = json.load(
            response
        )

    with ATTACK_JSON_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Saved JSON: "
        f"{ATTACK_JSON_PATH}"
    )

    return ATTACK_JSON_PATH


def main() -> None:
    timeout = 120.0

    if len(sys.argv) > 1:
        timeout = float(
            sys.argv[1]
        )

    path = (
        download_enterprise_attack(
            timeout=timeout,
        )
    )

    print()
    print("=" * 60)
    print(
        "MITRE ATT&CK Download Complete"
    )
    print("=" * 60)

    print(
        f"JSON : {path}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()