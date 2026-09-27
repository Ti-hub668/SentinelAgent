from app.intelligence.structured_enricher import (
    StructuredIntelligenceEnricher,
)
from app.models.finding import Finding
from app.schemas.agent_tools import (
    KEVRecordContext,
    NVDRecordContext,
    VulnerabilityIntelligenceResult,
)
from app.schemas.investigation_context import SentinelContextBundle


def lookup_vulnerability_intelligence(
    finding: Finding,
) -> VulnerabilityIntelligenceResult:
    """
    Retrieve structured vulnerability intelligence for a Finding.

    Current sources:
    - CISA KEV
    - NVD
    """

    enricher = StructuredIntelligenceEnricher()

    data = enricher.enrich(
        finding
    )

    identifiers = data["identifiers"]

    kev = data["cisa_kev"]
    nvd = data["nvd"]

    return VulnerabilityIntelligenceResult(
        finding_id=data["finding_id"],
        template_id=identifiers["template_id"],
        cve_ids=identifiers["cve_ids"],
        cwe_ids=identifiers["cwe_ids"],

        kev_matched=kev["matched"],
        kev_records=[
            KEVRecordContext(
                **record
            )
            for record in kev["records"]
        ],

        nvd_matched=nvd["matched"],
        nvd_records=[
            NVDRecordContext(
                **record
            )
            for record in nvd["records"]
        ],
    )

def lookup_context_intelligence(
    context: SentinelContextBundle,
) -> VulnerabilityIntelligenceResult:
    """
    Retrieve structured vulnerability intelligence using
    the Finding already stored in SentinelContextBundle.
    """

    enricher = StructuredIntelligenceEnricher()

    data = enricher.enrich(
        context.finding
    )

    identifiers = data["identifiers"]

    kev = data["cisa_kev"]
    nvd = data["nvd"]

    return VulnerabilityIntelligenceResult(
        finding_id=data["finding_id"],
        template_id=identifiers["template_id"],
        cve_ids=identifiers["cve_ids"],
        cwe_ids=identifiers["cwe_ids"],

        kev_matched=kev["matched"],
        kev_records=[
            KEVRecordContext(
                **record
            )
            for record in kev["records"]
        ],

        nvd_matched=nvd["matched"],
        nvd_records=[
            NVDRecordContext(
                **record
            )
            for record in nvd["records"]
        ],
    )