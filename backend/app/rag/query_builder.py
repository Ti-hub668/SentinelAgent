import json
from typing import Any


def _parse_identifier_list(
    value: Any,
) -> list[str]:
    """
    Support both SQLAlchemy JSON-string fields
    and ordinary Python lists used in tests.
    """

    if value is None:
        return []

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            str(item)
            .strip()
            .upper()
            for item in value
            if str(item).strip()
        ]

    if isinstance(
        value,
        str,
    ):
        stripped = (
            value.strip()
        )

        if not stripped:
            return []

        try:
            parsed = json.loads(
                stripped
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            parsed = None

        if isinstance(
            parsed,
            list,
        ):
            return [
                str(item)
                .strip()
                .upper()
                for item in parsed
                if str(item).strip()
            ]

        return [
            item.strip().upper()
            for item in stripped.split(
                ","
            )
            if item.strip()
        ]

    return []


def build_finding_query(
    finding: Any,
    max_evidence_length: int = 1000,
) -> str:
    """
    Build a security-aware RAG query.

    Priority:
    1. Exact security identifiers
    2. Scanner/template identity
    3. Finding semantics
    4. Evidence
    """

    def get_value(
        name: str,
    ) -> Any:
        if isinstance(
            finding,
            dict,
        ):
            return finding.get(
                name
            )

        return getattr(
            finding,
            name,
            None,
        )

    title = get_value(
        "title"
    )

    finding_type = get_value(
        "finding_type"
    )

    severity = get_value(
        "severity"
    )

    description = get_value(
        "description"
    )

    evidence = get_value(
        "evidence"
    )

    template_id = get_value(
        "template_id"
    )

    cve_ids = (
        _parse_identifier_list(
            get_value(
                "cve_ids"
            )
        )
    )

    cwe_ids = (
        _parse_identifier_list(
            get_value(
                "cwe_ids"
            )
        )
    )

    parts: list[str] = []

    # Exact identifiers are intentionally
    # placed first for hybrid retrieval.
    if cve_ids:
        parts.append(
            "CVE identifiers: "
            + ", ".join(
                cve_ids
            )
        )

    if cwe_ids:
        parts.append(
            "CWE identifiers: "
            + ", ".join(
                cwe_ids
            )
        )

    if template_id:
        parts.append(
            "Scanner template: "
            f"{template_id}"
        )

    if title:
        parts.append(
            f"Finding title: {title}"
        )

    if finding_type:
        parts.append(
            "Finding type: "
            f"{finding_type}"
        )

    if severity:
        parts.append(
            f"Severity: {severity}"
        )

    if description:
        parts.append(
            "Description: "
            f"{description}"
        )

    if evidence:
        evidence_text = str(
            evidence
        )

        if (
            len(evidence_text)
            > max_evidence_length
        ):
            evidence_text = (
                evidence_text[
                    :max_evidence_length
                ]
                + "..."
            )

        parts.append(
            "Evidence: "
            f"{evidence_text}"
        )

    if not parts:
        raise ValueError(
            "Finding does not contain "
            "usable retrieval fields."
        )

    return "\n".join(
        parts
    )