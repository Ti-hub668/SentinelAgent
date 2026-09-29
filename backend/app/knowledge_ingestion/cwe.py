import sys
import urllib.request
import zipfile
from pathlib import Path


CWE_OUTPUT_DIR = Path(
    "knowledge/official/mitre/cwe"
)

CWE_ZIP_PATH = (
    CWE_OUTPUT_DIR
    / "cwec_latest.xml.zip"
)

CWE_XML_PATH = (
    CWE_OUTPUT_DIR
    / "cwec_latest.xml"
)

CWE_XML_ZIP_URL = (
    "https://"
    "cwe.mitre.org/data/xml/"
    "cwec_latest.xml.zip"
)


def download_cwe(
    timeout: float = 60.0,
) -> Path:
    """
    Download the latest official MITRE CWE XML archive.
    """

    CWE_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = urllib.request.Request(
        CWE_XML_ZIP_URL,
        headers={
            "User-Agent":
                "SentinelAgent/0.1",

            "Accept":
                "application/zip",
        },
    )

    print(
        "Downloading MITRE CWE..."
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        data = response.read()

    with CWE_ZIP_PATH.open(
        "wb",
    ) as file:
        file.write(data)

    print(
        f"Saved archive: "
        f"{CWE_ZIP_PATH}"
    )

    return CWE_ZIP_PATH


def extract_cwe(
    archive_path: Path = CWE_ZIP_PATH,
) -> Path:
    """
    Extract the CWE XML file from the official ZIP.

    The extracted file is written to a stable SentinelAgent
    path so later stages do not depend on the upstream filename.
    """

    if not archive_path.exists():
        raise FileNotFoundError(
            "CWE archive not found: "
            f"{archive_path}"
        )

    with zipfile.ZipFile(
        archive_path,
        "r",
    ) as archive:
        xml_members = [
            item
            for item in archive.infolist()
            if (
                not item.is_dir()
                and item.filename
                .lower()
                .endswith(".xml")
            )
        ]

        if not xml_members:
            raise ValueError(
                "CWE archive contains no XML file."
            )

        # The official package normally contains one main
        # CWE XML file. Prefer the largest XML member if more
        # than one is present.
        xml_member = max(
            xml_members,
            key=lambda item:
                item.file_size,
        )

        xml_data = archive.read(
            xml_member
        )

    CWE_XML_PATH.write_bytes(
        xml_data
    )

    print(
        f"Extracted XML: "
        f"{CWE_XML_PATH}"
    )

    print(
        f"Original member: "
        f"{xml_member.filename}"
    )

    return CWE_XML_PATH


def main() -> None:
    timeout = 60.0

    if len(sys.argv) > 1:
        timeout = float(
            sys.argv[1]
        )

    archive_path = download_cwe(
        timeout=timeout,
    )

    xml_path = extract_cwe(
        archive_path
    )

    print()
    print("=" * 60)
    print(
        "MITRE CWE Download Complete"
    )
    print("=" * 60)

    print(
        f"Archive : {archive_path}"
    )

    print(
        f"XML     : {xml_path}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()