import json
import sys
from pathlib import Path
from typing import Any

from app.knowledge_ingestion.schema import (
    SecurityKnowledgeRecord,
)


RAW_DIR = Path("knowledge/official/nvd")
PROCESSED_DIR = Path("knowledge/processed/nvd")


def get_english_description(cve: dict) -> str:
    for item in cve.get("descriptions", []):
        if item.get("lang") == "en":
            return item.get("value", "")

    return ""


def get_cwe_ids(cve: dict) -> list[str]:
    cwe_ids = []

    for weakness in cve.get("weaknesses", []):
        for description in weakness.get(
            "description",
            [],
        ):
            value = description.get("value")

            if (
                isinstance(value, str)
                and value.startswith("CWE-")
            ):
                cwe_ids.append(value)

    return list(dict.fromkeys(cwe_ids))


def get_cvss(cve: dict) -> tuple[float | None, str | None]:
    metrics = cve.get("metrics", {})

    metric_order = [
        "cvssMetricV40",
        "cvssMetricV31",
        "cvssMetricV30",
        "cvssMetricV2",
    ]

    for metric_name in metric_order:
        entries = metrics.get(
            metric_name,
            [],
        )

        if not entries:
            continue

        # Prefer NVD's own assessment when present.
        metric = next(
            (
                item
                for item in entries
                if item.get("source") == "nvd@nist.gov"
            ),
            entries[0],
        )

        cvss_data = metric.get(
            "cvssData",
            {},
        )

        score = cvss_data.get(
            "baseScore"
        )

        severity = (
            cvss_data.get("baseSeverity")
            or metric.get("baseSeverity")
        )

        if score is not None:
            return (
                float(score),
                (
                    str(severity).lower()
                    if severity
                    else None
                ),
            )

    return None, None


def get_references(cve: dict) -> list[str]:
    references = []

    for item in cve.get("references", []):
        url = item.get("url")

        if url:
            references.append(url)

    return references


def get_affected_products(cve: dict) -> list[str]:
    products = []

    def walk_nodes(nodes: list[dict[str, Any]]) -> None:
        for node in nodes:
            for cpe_match in node.get(
                "cpeMatch",
                [],
            ):
                criteria = cpe_match.get(
                    "criteria"
                )

                if criteria:
                    products.append(criteria)

            children = node.get(
                "nodes",
                [],
            )

            if children:
                walk_nodes(children)

    for configuration in cve.get(
        "configurations",
        [],
    ):
        walk_nodes(
            configuration.get(
                "nodes",
                [],
            )
        )

    return list(dict.fromkeys(products))


def normalize_nvd(data: dict) -> SecurityKnowledgeRecord:
    vulnerabilities = data.get(
        "vulnerabilities",
        [],
    )

    if not vulnerabilities:
        raise ValueError(
            "NVD response contains no vulnerabilities."
        )

    cve = vulnerabilities[0].get(
        "cve",
        {},
    )

    cve_id = cve.get("id")

    if not cve_id:
        raise ValueError(
            "NVD CVE record has no CVE ID."
        )

    description = get_english_description(
        cve
    )

    cwe_ids = get_cwe_ids(
        cve
    )

    cvss_score, severity = get_cvss(
        cve
    )

    references = get_references(
        cve
    )

    affected_products = get_affected_products(
        cve
    )

    return SecurityKnowledgeRecord(
        id=f"nvd:{cve_id}",
        source="nvd",
        source_id=cve_id,
        knowledge_type="vulnerability",
        title=cve_id,
        description=description,
        severity=severity,
        cvss_score=cvss_score,
        cwe_ids=cwe_ids,
        cve_ids=[cve_id],
        affected_products=affected_products,
        source_url=(
            f"https://nvd.nist.gov/vuln/detail/{cve_id}"
        ),
        published_at=cve.get("published"),
        modified_at=cve.get("lastModified"),
        tags=[
            "nvd",
            "cve",
            "vulnerability",
        ],
        metadata={
            "vuln_status": cve.get(
                "vulnStatus"
            ),
            "references": references,
        },
    )


def save_record(
    record: SecurityKnowledgeRecord,
) -> Path:
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        PROCESSED_DIR
        / f"{record.source_id}.json"
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


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python -m "
            "app.knowledge_ingestion.nvd_normalizer "
            "CVE-YYYY-NNNN"
        )
        raise SystemExit(1)

    cve_id = sys.argv[1].strip().upper()

    input_path = (
        RAW_DIR / f"{cve_id}.json"
    )

    if not input_path.exists():
        raise FileNotFoundError(
            f"NVD raw file not found: {input_path}"
        )

    with input_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    record = normalize_nvd(
        data
    )

    output_path = save_record(
        record
    )

    print()
    print("NVD Normalization")
    print("=" * 60)
    print(
        f"CVE       : {record.source_id}"
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
    print(
        "References: "
        f"{len(record.metadata.get('references', []))}"
    )
    print(
        f"Saved     : {output_path}"
    )


if __name__ == "__main__":
    main()