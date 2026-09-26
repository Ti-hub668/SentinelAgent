import json
import re

from pydantic import ValidationError

from app.ai.evidence_prompt_builder import build_evidence_assessment_prompt
from app.ai.llm_client import call_llm
from app.schemas.ai_analysis import AIAnalysisInput
from app.schemas.evidence_assessment import EvidenceAssessmentResult

def apply_category_guardrail(
    data: AIAnalysisInput,
    result: EvidenceAssessmentResult,
) -> EvidenceAssessmentResult:
    """
    对 Finding Category 做最小确定性约束。

    只有当模型返回 ambiguous_security_signal，
    但 Finding 本身已经明确声明漏洞语义时，
    才将 Category 修正为 vulnerability。

    Evidence Status 和 Preliminary Verdict 不做修改。
    """

    if (
        result.finding_category
        != "ambiguous_security_signal"
    ):
        return result

    text = " ".join(
        [
            data.title or "",
            data.description or "",
        ]
    )

    explicit_cve = bool(
        re.search(
            r"\bCVE-\d{4}-\d{4,7}\b",
            text,
            flags=re.IGNORECASE,
        )
    )

    explicit_vulnerability = (
        "vulnerability" in text.lower()
        or "漏洞" in text
    )

    if explicit_cve or explicit_vulnerability:
        return result.model_copy(
            update={
                "finding_category": "vulnerability"
            }
        )

    return result

def apply_api_docs_exposure_guardrail(
    data: AIAnalysisInput,
    result: EvidenceAssessmentResult,
) -> EvidenceAssessmentResult:
    """
    对公开 API 文档暴露类 Finding 做确定性核验。

    仅当 Finding 明确属于 Swagger / ReDoc / API Docs，
    且 Evidence 证明对应资源可正常访问时，
    修正为 exposure / confirmed / likely_true_positive。
    """

    title = (data.title or "").lower()
    evidence = data.evidence or ""
    evidence_lower = evidence.lower()

    api_docs_signal = any(
        keyword in title
        for keyword in [
            "swagger",
            "redoc",
            "api docs",
            "api documentation",
        ]
    )

    if not api_docs_signal:
        return result

    accessible_signal = (
        "http/1.1 200 ok" in evidence_lower
        or "http/2 200" in evidence_lower
        or "swagger" in evidence_lower
        or "redoc" in evidence_lower
        or "openapi" in evidence_lower
    )

    if not accessible_signal:
        return result

    return result.model_copy(
        update={
            "finding_category": "exposure",
            "evidence_status": "confirmed",
            "preliminary_verdict":
                "likely_true_positive",
            "reason": (
                "The Finding reports publicly accessible "
                "API documentation, and the captured "
                "evidence confirms that the Swagger/ReDoc/"
                "API documentation resource is accessible."
            ),
        }
    )

def apply_missing_header_guardrail(
    data: AIAnalysisInput,
    result: EvidenceAssessmentResult,
) -> EvidenceAssessmentResult:
    """
    对 Nuclei HTTP Missing Security Headers 结果进行确定性核验。

    只有同时满足：
    1. Evidence 来自 http-missing-security-headers 模板；
    2. Nuclei 明确给出 missing-header matcher；
    3. HTTP Response Evidence 中确实不存在对应 Header；

    才将结果修正为：
    security_misconfiguration / confirmed / likely_true_positive
    """

    evidence = data.evidence or ""

    if (
        "Template ID: http-missing-security-headers"
        not in evidence
    ):
        return result

    matcher_prefix = "Matcher Name:"

    matcher_name = None

    for line in evidence.splitlines():
        if line.startswith(matcher_prefix):
            matcher_name = line.split(
                ":",
                1,
            )[1].strip()
            break

    if not matcher_name:
        return result

    expected_condition = (
        "Scanner Match Condition: "
        "Nuclei reported the missing-header matcher "
        f"'{matcher_name}' as matched."
    )

    if expected_condition not in evidence:
        return result

    response_marker = "HTTP Response Evidence:"

    if response_marker not in evidence:
        return result

    response = evidence.split(
        response_marker,
        1,
    )[1]

    response = response.replace(
        "\r\n",
        "\n",
    )

    # HTTP Header 部分位于响应体之前
    header_section = response.split(
        "\n\n",
        1,
    )[0]

    normalized_header = matcher_name.strip().lower()

    header_present = any(
        line.lower().startswith(
            normalized_header + ":"
        )
        for line in header_section.splitlines()
    )

    if header_present:
        # Nuclei 说 Header 缺失，
        # 但实际响应中却明确存在。
        return result.model_copy(
            update={
                "finding_category":
                    "security_misconfiguration",
                "evidence_status":
                    "contradicted",
                "preliminary_verdict":
                    "likely_false_positive",
                "reason": (
                    f"Nuclei reported the missing-header "
                    f"matcher '{matcher_name}' as matched, "
                    f"but the HTTP response contains the "
                    f"'{matcher_name}' header."
                ),
            }
        )

    # Nuclei 明确命中缺失 Header matcher，
    # 且完整 HTTP Header 部分确实没有该 Header。
    return result.model_copy(
        update={
            "finding_category":
                "security_misconfiguration",
            "evidence_status":
                "confirmed",
            "preliminary_verdict":
                "likely_true_positive",
            "reason": (
                f"Nuclei reported the missing-header "
                f"matcher '{matcher_name}' as matched, "
                f"and the captured HTTP response headers "
                f"do not contain the '{matcher_name}' "
                f"header."
            ),
        }
    )

def clean_evidence_json(raw_text: str) -> str:
    text = raw_text.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()

def normalize_confidence_value(
    parsed: dict,
) -> dict:
    """
    兼容 LLM 偶尔使用百分制 confidence 的情况。

    正常范围：
    0.0 ~ 1.0

    如果模型明确返回：
    1 < confidence <= 100

    则按百分制转换：
    50 -> 0.50
    85 -> 0.85
    95 -> 0.95
    """

    confidence = parsed.get("confidence")

    if isinstance(confidence, (int, float)):
        if 1 < confidence <= 100:
            parsed["confidence"] = confidence / 100.0

    return parsed

def assess_evidence(
    data: AIAnalysisInput,
) -> EvidenceAssessmentResult:
    prompt = build_evidence_assessment_prompt(data)

    raw_response = call_llm(
        prompt,
        response_schema=EvidenceAssessmentResult,
    )

    cleaned_response = clean_evidence_json(raw_response)

    try:
        parsed = json.loads(cleaned_response)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "LLM returned invalid Evidence Assessment JSON"
        ) from exc

    parsed = normalize_confidence_value(parsed)

    try:
        result = EvidenceAssessmentResult.model_validate(
            parsed
        )

    except ValidationError as exc:
        print("\n" + "=" * 80)
        print("EVIDENCE SCHEMA VALIDATION FAILED")
        print(f"Finding ID: {data.finding_id}")
        print("Raw parsed response:")
        print(
            json.dumps(
                parsed,
                ensure_ascii=False,
                indent=2,
            )
        )
        print("\nValidation error:")
        print(exc)
        print("=" * 80 + "\n")

        raise RuntimeError(
            "LLM response does not match "
            "EvidenceAssessmentResult schema"
        ) from exc

    result = apply_category_guardrail(
        data,
        result,
    )

    result = apply_api_docs_exposure_guardrail(
        data,
        result,
    )

    result = apply_missing_header_guardrail(
        data,
        result,
    )

    return result