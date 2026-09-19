import time

from app.ai.prompt_builder import PROMPT_VERSION
from app.ai.risk_analyst import analyze_finding
from app.schemas.ai_analysis import AIAnalysisInput


def main() -> None:
    """
    对 holdout_002 进行辅助风险字段消融实验。

    保持 Title / Description / Evidence 不变，
    仅中和 Severity / Risk Score / Risk Level / Risk Reason。
    """

    analysis_input = AIAnalysisInput(
        finding_id=2002,
        source="nuclei",
        finding_type="vulnerability",
        severity="unknown",
        target="192.168.2.20",
        title=(
            "Security Misconfiguration: "
            "Missing Content Security Policy Header"
        ),
        description=(
            "A security configuration weakness was detected. "
            "The application does not configure the "
            "Content-Security-Policy security header."
        ),

        evidence=(
            "The inspected HTTP response headers directly confirmed "
            "that the Content-Security-Policy security header was absent."
        ),
        remediation=(
            "Review whether an appropriate Content Security "
            "Policy should be configured."
        ),
        risk_score=0,
        risk_level="unknown",
        risk_reason="N/A",
    )

    print("=" * 60)
    print("SentinelAgent Ablation Test")
    print("=" * 60)

    print(f"Prompt Version : {PROMPT_VERSION}")
    print("Case           : holdout_002")
    print("Experiment     : neutralized risk fields")

    print()
    print("Changed Fields:")
    print("  severity     : low -> unknown")
    print("  risk_score   : 30 -> 0")
    print("  risk_level   : low -> unknown")
    print("  risk_reason  : confirmed missing -> N/A")

    print()
    print("Expected Verdict: likely_true_positive")

    print()
    print("Running model...")
    print()

    start_time = time.perf_counter()

    result = analyze_finding(analysis_input)

    elapsed = time.perf_counter() - start_time

    print("-" * 60)
    print("Result")
    print("-" * 60)

    print(f"Actual Verdict : {result.verdict}")
    print(f"Confidence     : {result.confidence:.2f}")
    print(f"Latency        : {elapsed:.2f}s")
    print(f"Summary        : {result.summary}")
    print(f"Reason         : {result.risk_explanation}")
    print(f"Action         : {result.recommended_action}")

    print()
    print("-" * 60)

    if result.verdict == "likely_true_positive":
        print(
            "Observation: verdict changed after explicitly "
            "framing the finding as a security misconfiguration."
        )
    else:
        print(
            "Observation: explicit security-misconfiguration "
            "framing did not change the verdict."
        )

    print("=" * 60)


if __name__ == "__main__":
    main()