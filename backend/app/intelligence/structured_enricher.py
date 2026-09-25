import json
from typing import Any

from app.knowledge_ingestion.kev_lookup import KEVLookup
from app.knowledge_ingestion.nvd_lookup import NVDLookup
from app.models.finding import Finding


class StructuredIntelligenceEnricher:
    """
    Enrich a Finding with structured security intelligence.

    Current sources:
    - CISA KEV
    - NVD

    Planned sources:
    - CWE
    - MITRE ATT&CK
    """

    def __init__(self) -> None:
        self.kev_lookup = KEVLookup()
        self.nvd_lookup = NVDLookup()

    @staticmethod
    def _parse_json_list(
        value: str | None,
    ) -> list[str]:
        if not value:
            return []

        try:
            parsed = json.loads(value)

        except json.JSONDecodeError:
            return []

        if not isinstance(parsed, list):
            return []

        return [
            str(item).strip()
            for item in parsed
            if str(item).strip()
        ]

    def enrich(
        self,
        finding: Finding,
    ) -> dict[str, Any]:

        cve_ids = self._parse_json_list(
            finding.cve_ids
        )

        cwe_ids = self._parse_json_list(
            finding.cwe_ids
        )

        kev_records = []
        nvd_records = []

        for cve_id in cve_ids:
            # -------------------------
            # CISA KEV exact lookup
            # -------------------------
            kev_record = self.kev_lookup.get(
                cve_id
            )

            if kev_record is not None:
                kev_records.append(
                    {
                        "cve_id": cve_id,
                        "known_exploited":
                            kev_record.known_exploited,
                        "title":
                            kev_record.title,
                        "affected_products":
                            kev_record.affected_products,
                        "cwe_ids":
                            kev_record.cwe_ids,
                        "required_action":
                            kev_record.remediation,
                        "date_added":
                            kev_record.metadata.get(
                                "date_added"
                            ),
                        "due_date":
                            kev_record.metadata.get(
                                "due_date"
                            ),
                        "known_ransomware_campaign_use":
                            kev_record.metadata.get(
                                "known_ransomware_campaign_use"
                            ),
                    }
                )

            # -------------------------
            # NVD exact lookup
            # -------------------------
            nvd_record = self.nvd_lookup.get(
                cve_id
            )

            if nvd_record is not None:
                nvd_records.append(
                    {
                        "cve_id":
                            nvd_record.source_id,
                        "description":
                            nvd_record.description,
                        "cvss_score":
                            nvd_record.cvss_score,
                        "severity":
                            nvd_record.severity,
                        "cwe_ids":
                            nvd_record.cwe_ids,
                        "affected_products":
                            nvd_record.affected_products,
                        "references":
                            nvd_record.metadata.get(
                                "references",
                                [],
                            ),
                        "published_at":
                            nvd_record.published_at,
                        "modified_at":
                            nvd_record.modified_at,
                        "vuln_status":
                            nvd_record.metadata.get(
                                "vuln_status"
                            ),
                    }
                )

        return {
            "finding_id": finding.id,

            "identifiers": {
                "template_id":
                    finding.template_id,
                "cve_ids":
                    cve_ids,
                "cwe_ids":
                    cwe_ids,
            },

            "cisa_kev": {
                "matched":
                    len(kev_records) > 0,
                "records":
                    kev_records,
            },

            "nvd": {
                "matched":
                    len(nvd_records) > 0,
                "records":
                    nvd_records,
            },
        }