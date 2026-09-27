from app.agent.state import SentinelInvestigationState
from app.schemas.grounding import (
    GroundingCheck,
    GroundingResult,
)


def validate_grounding(
    state: SentinelInvestigationState,
) -> GroundingResult:
    """
    Validate whether the final AI verdict is sufficiently
    supported by investigation evidence.

    This validator is deterministic and does not call an LLM.
    """

    context = state.get("context")
    evidence = state.get("evidence_assessment")
    enrichment = state.get("risk_enrichment")

    if context is None:
        raise RuntimeError(
            "Investigation context is missing."
        )

    if evidence is None:
        raise RuntimeError(
            "Evidence assessment is missing."
        )

    if enrichment is None:
        raise RuntimeError(
            "Risk enrichment is missing."
        )

    checks: list[GroundingCheck] = []

    # --------------------------------------------------
    # Rule 1: Evidence support
    # --------------------------------------------------

    evidence_supported = (
        evidence.evidence_status
        == "confirmed"
    )

    checks.append(
        GroundingCheck(
            rule="confirmed_evidence",
            passed=evidence_supported,
            reason=(
                "Finding evidence is confirmed."
                if evidence_supported
                else (
                    "Finding evidence is not confirmed "
                    f"({evidence.evidence_status})."
                )
            ),
        )
    )

    # --------------------------------------------------
    # Rule 2: Verdict consistency
    # --------------------------------------------------

    verdict_consistent = not (
        enrichment.final_verdict
        == "likely_true_positive"
        and evidence.preliminary_verdict
        == "likely_false_positive"
    )

    checks.append(
        GroundingCheck(
            rule="verdict_consistency",
            passed=verdict_consistent,
            reason=(
                "Evidence and enrichment verdicts are consistent."
                if verdict_consistent
                else (
                    "Risk enrichment promotes a finding to "
                    "likely_true_positive despite a "
                    "likely_false_positive evidence verdict."
                )
            ),
        )
    )

    # --------------------------------------------------
    # Rule 3: Known-exploitation grounding
    # --------------------------------------------------

    intelligence = state.get(
        "intelligence_result"
    )

    intelligence_supported = True

    if intelligence is not None:
        intelligence_text = (
            enrichment.intelligence_context
            or ""
        ).lower()

        # Explicit negative statements must not be
        # interpreted as positive exploitation claims.
        negative_exploitation_phrases = (
            "no known exploitation",
            "does not have known exploitation",
            "not known to be exploited",
            "no evidence of active exploitation",
            "no evidence of known exploitation",
            "not actively exploited",
            "no cisa kev",
            "not listed in cisa kev",
            "no kev entries",
            "no cisa kev entries",
        )

        positive_exploitation_phrases = (
            "is actively exploited",
            "actively exploited in the wild",
            "known to be exploited",
            "known exploited vulnerability",
            "confirmed active exploitation",
            "listed in cisa kev",
            "is in cisa kev",
            "included in cisa kev",
        )

        has_negative_statement = any(
            phrase in intelligence_text
            for phrase in negative_exploitation_phrases
        )

        has_positive_statement = any(
            phrase in intelligence_text
            for phrase in positive_exploitation_phrases
        )

        claims_known_exploitation = (
            has_positive_statement
            and not has_negative_statement
        )

        kev_records = getattr(
            intelligence,
            "kev_records",
            [],
        )

        if (
            claims_known_exploitation
            and not kev_records
        ):
            intelligence_supported = False

    checks.append(
        GroundingCheck(
            rule="known_exploitation_grounding",
            passed=intelligence_supported,
            reason=(
                "Known-exploitation claims are supported "
                "by structured intelligence or no such "
                "claim was made."
                if intelligence_supported
                else (
                    "The analysis claims known exploitation "
                    "without supporting KEV intelligence."
                )
            ),
        )
    )

    # --------------------------------------------------
    # Calculate grounding score
    # --------------------------------------------------

    passed_count = sum(
        check.passed
        for check in checks
    )

    score = (
        passed_count
        / len(checks)
    )

    # --------------------------------------------------
    # Determine grounding status
    # --------------------------------------------------

    if score == 1.0:
        status = "supported"

    elif score >= 0.5:
        status = "partially_supported"

    else:
        status = "unsupported"

    original_verdict = (
        enrichment.final_verdict
    )

    grounded_verdict = (
        original_verdict
    )

    requires_human_review = False

    # Fail-safe:
    # unsupported conclusions must never be promoted
    # automatically.
    if status == "unsupported":
        grounded_verdict = "needs_review"
        requires_human_review = True

    elif status == "partially_supported":
        requires_human_review = True

    return GroundingResult(
        finding_id=context.finding.id,
        status=status,
        score=score,
        checks=checks,
        original_verdict=original_verdict,
        grounded_verdict=grounded_verdict,
        requires_human_review=requires_human_review,
        reason=(
            f"{passed_count}/{len(checks)} "
            "grounding checks passed."
        ),
    )