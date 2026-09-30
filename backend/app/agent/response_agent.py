import json

from pydantic import ValidationError

from app.ai.llm_client import call_llm
from app.agent.decision_agent import (
    make_security_decision,
)
from app.agent.response_prompt_builder import (
    build_response_prompt,
)
from app.agent.state import (
    SentinelInvestigationState,
)
from app.schemas.agent_decision import (
    AgentDecisionInput,
)
from app.schemas.response_plan import (
    ResponsePlan,
    ToolRequest,
)


def _clean_json(
    raw_text: str,
) -> str:
    text = raw_text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def build_security_decision(
    state: SentinelInvestigationState,
):
    """
    Adapt grounded investigation result into the
    existing deterministic Decision Agent.
    """

    context = state.get("context")
    grounding = state.get("grounding_result")
    enrichment = state.get("risk_enrichment")

    if context is None:
        raise RuntimeError(
            "Investigation context is missing."
        )

    if grounding is None:
        raise RuntimeError(
            "Grounding result is missing."
        )

    if enrichment is None:
        raise RuntimeError(
            "Risk enrichment is missing."
        )

    grounded_verdict = (
        grounding.grounded_verdict
    )

    confidence = enrichment.confidence

    # Grounding uncertainty must lower automatic trust.
    if grounding.requires_human_review:
        confidence = min(
            confidence,
            0.79,
        )

    decision_input = AgentDecisionInput(
        finding_id=context.finding.id,

        # This investigation is not yet persisted as an
        # AIAnalysis database record in the LangGraph path.
        # A neutral placeholder is used only inside this
        # in-memory decision adapter.
        ai_analysis_id=0,

        verdict=grounded_verdict,
        confidence=confidence,

        severity=context.finding.severity,

        risk_score=(
            context.deterministic_risk.risk_score
            or 0
        ),

        risk_level=(
            context.deterministic_risk.risk_level
            or "unknown"
        ),
    )

    return make_security_decision(
        decision_input
    )


def generate_response_plan(
    state: SentinelInvestigationState,
    *,
    include_tool_capabilities: bool = False,
) -> ResponsePlan:
    """
    Generate a dry-run response plan from a grounded
    investigation result.

    No tool is executed in this function.
    """

    context = state.get("context")
    grounding = state.get("grounding_result")
    enrichment = state.get("risk_enrichment")

    if context is None:
        raise RuntimeError(
            "Investigation context is missing."
        )

    if grounding is None:
        raise RuntimeError(
            "Grounding result is missing."
        )

    if enrichment is None:
        raise RuntimeError(
            "Risk enrichment is missing."
        )

    decision = build_security_decision(
        state
    )

    prompt = build_response_prompt(
        finding_id=context.finding.id,
        title=context.finding.title,
        severity=context.finding.severity,
        target=context.finding.target,
        grounded_verdict=(
            grounding.grounded_verdict
        ),
        grounding_status=grounding.status,
        grounding_reason=grounding.reason,
        risk_summary=enrichment.summary,
        recommended_action=(
            enrichment.recommended_action
        ),
        decision=decision,
        include_tool_capabilities=include_tool_capabilities,
    )

    raw_response = call_llm(
        prompt,
        response_schema=ResponsePlan,
    )

    cleaned = _clean_json(
        raw_response
    )

    try:
        parsed = json.loads(
            cleaned
        )

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Response Agent returned invalid JSON."
        ) from exc

    try:
        plan = ResponsePlan.model_validate(
            parsed
        )

    except ValidationError as exc:
        raise RuntimeError(
            "Response Agent output does not match "
            "ResponsePlan schema."
        ) from exc

    # --------------------------------------------------
    # Deterministic safety guardrails
    # --------------------------------------------------

    plan = plan.model_copy(
        update={
            "finding_id":
                context.finding.id,

            "grounded_verdict":
                grounding.grounded_verdict,

            "decision_action":
                decision.action,

            "priority":
                decision.priority,

            "requires_human_review": (
                decision.requires_human_review
                or grounding.requires_human_review
            ),

            # Response Agent is ALWAYS dry-run.
            "dry_run": True,
        }
    )

       # --------------------------------------------------
    # Deterministic response safety guardrails
    # --------------------------------------------------

    # Human-review-required plans must never retain
    # disruptive containment requests.
    if plan.requires_human_review:
        safe_requests = [
            request
            for request in plan.tool_requests
            if request.tool_name
            in {
                "manual_review",
                "create_ticket",
                "notify",
            }
        ]

        plan = plan.model_copy(
            update={
                "tool_requests": safe_requests,
            }
        )

    # --------------------------------------------------
    # Human review must be represented explicitly.
    #
    # Do not rely on the LLM to remember to generate
    # a manual_review ToolRequest.
    # --------------------------------------------------

    if (
        plan.requires_human_review
        and not any(
            request.tool_name
            == "manual_review"
            for request in plan.tool_requests
        )
    ):
        manual_review_request = ToolRequest(
            tool_name="manual_review",
            target=(
                f"finding:{context.finding.id}"
            ),
            reason=(
                "The grounded investigation or "
                "decision policy requires explicit "
                "human security review before further "
                "response actions are released."
            ),
            parameters={
                "finding_id":
                    context.finding.id,
                "grounded_verdict":
                    grounding.grounded_verdict,
            },
        )

        plan = plan.model_copy(
            update={
                "tool_requests": [
                    *plan.tool_requests,
                    manual_review_request,
                ]
            }
        )

    return plan