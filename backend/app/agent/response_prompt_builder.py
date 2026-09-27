from app.schemas.agent_decision import (
    AgentDecisionOutput,
)
from app.schemas.response_plan import ResponsePlan


def build_response_prompt(
    *,
    finding_id: int,
    title: str,
    severity: str,
    target: str,
    grounded_verdict: str,
    grounding_status: str,
    grounding_reason: str,
    risk_summary: str,
    recommended_action: str,
    decision: AgentDecisionOutput,
) -> str:
    """
    Build a constrained prompt for the Response Agent.

    The model may recommend actions but must never
    claim that an action has actually been executed.
    """

    schema = ResponsePlan.model_json_schema()

    return f"""
You are the Response Planning component of SentinelAgent.

Your job is to produce a DRY-RUN security response plan.

IMPORTANT SECURITY RULES:

1. You must NOT execute any action.
2. You must NOT claim that an IP was blocked.
3. You must NOT claim that a ticket was created.
4. You must NOT claim that a notification was sent.
5. You may only propose Tool Requests.
6. The final execution decision belongs to the Policy Engine.
7. If evidence is uncertain or human review is required,
   prefer manual_review over aggressive containment.
8. Use only the supplied investigation facts.
9. Do not invent CVEs, exploitation status, assets, users,
   hosts, credentials, or attack details.

Finding ID:
{finding_id}

Finding:
{title}

Severity:
{severity}

Target:
{target}

Grounded Verdict:
{grounded_verdict}

Grounding Status:
{grounding_status}

Grounding Reason:
{grounding_reason}

Risk Summary:
{risk_summary}

Recommended Security Action:
{recommended_action}

Existing Decision Agent Result:
action={decision.action}
priority={decision.priority}
reason={decision.reason}
requires_human_review={decision.requires_human_review}
recommended_next_step={decision.recommended_next_step}

Return ONLY valid JSON matching this schema:

{schema}
""".strip()