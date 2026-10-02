from app.ai.prompt_builder import build_risk_analysis_prompt
from app.schemas.ai_analysis import AIAnalysisInput


data = AIAnalysisInput(
    finding_id=999999,
    source="nuclei",
    finding_type="vulnerability",
    title="CVE Test Finding",
    severity="high",
    target="127.0.0.1",
    description="Synthetic test finding.",
    evidence="Scanner evidence for testing.",
    remediation="Apply vendor remediation.",
    risk_score=80,
    risk_level="high",
    risk_reason="Synthetic test risk.",
)

structured_intelligence = """
CVE: CVE-2026-7273
CISA KEV Matched: true
Known Exploited: true
CWE: CWE-121
Affected Product: Zyxel GS1900 Series Switches
""".strip()


# Test 1：有 Structured Intelligence
prompt_with_intelligence = build_risk_analysis_prompt(
    data,
    structured_intelligence=structured_intelligence,
)

assert "五、结构化安全情报" in prompt_with_intelligence
assert "CVE-2026-7273" in prompt_with_intelligence
assert "Known Exploited: true" in prompt_with_intelligence


# Test 2：没有 Structured Intelligence
prompt_without_intelligence = build_risk_analysis_prompt(
    data,
)

assert "五、结构化安全情报" not in prompt_without_intelligence
assert "CVE-2026-7273" not in prompt_without_intelligence


print("Structured Intelligence Prompt Test: PASS")