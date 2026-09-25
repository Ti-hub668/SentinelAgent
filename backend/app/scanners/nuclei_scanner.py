import ipaddress
import json
import subprocess
from urllib.parse import urlparse


NUCLEI_SCAN_PROFILES = {
    "fast": [
        "technologies",
    ],
    "security": [
        "exposures",
        "misconfiguration",
        "exposed-panels",
    ],
    "full": [
        "cves",
        "default-logins",
        "exposed-panels",
        "exposures",
        "misconfiguration",
        "technologies",
    ],
}


def get_nuclei_template_paths(profile: str) -> list[str]:
    """
    根据扫描 Profile 返回对应的 Nuclei 模板目录。
    """

    if profile not in NUCLEI_SCAN_PROFILES:
        raise ValueError(
            f"Unsupported Nuclei scan profile: {profile}"
        )

    base_path = r"C:\Tools\nuclei-templates\http"

    return [
        rf"{base_path}\{template_name}"
        for template_name
        in NUCLEI_SCAN_PROFILES[profile]
    ]


def validate_nuclei_target(target: str) -> str:
    """
    校验 Nuclei 扫描目标。

    当前开发阶段仅允许：
    - localhost
    - 回环地址
    - 私有网络 IP
    """

    parsed = urlparse(target)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            "Nuclei target must use http or https"
        )

    hostname = parsed.hostname

    if hostname is None:
        raise ValueError(
            "Invalid Nuclei target"
        )

    if hostname.lower() == "localhost":
        return target

    try:
        ip = ipaddress.ip_address(hostname)

    except ValueError:
        raise ValueError(
            "当前开发版本仅允许 localhost 或私有 IP"
        )

    if ip.is_loopback or ip.is_private:
        return target

    raise ValueError(
        "开发环境仅允许扫描本机或私有网络中的授权资产"
    )


def run_nuclei(
    target: str,
    profile: str = "fast"
) -> list[dict]:
    """
    调用 Nuclei 扫描 Web 服务。

    profile:
    - fast
    - security
    - full
    """

    validate_nuclei_target(
        target
    )

    template_paths = (
        get_nuclei_template_paths(
            profile
        )
    )

    command = [
        "nuclei",
        "-u",
        target,
        "-jsonl",
        "-silent",
        "-nc",
        "-duc",
        "-timeout",
        "5",
        "-retries",
        "1",
    ]

    for template_path in template_paths:
        command.extend([
            "-t",
            template_path,
        ])

    timeout_seconds = {
        "fast": 60,
        "security": 120,
        "full": 180,
    }.get(
        profile,
        60
    )

    print(
        f"Nuclei profile: {profile}"
    )

    print(
        f"Nuclei target: {target}"
    )

    print(
        "Nuclei templates:"
    )

    for template_path in template_paths:
        print(
            f"  - {template_path}"
        )

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False
        )

    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"Nuclei scan timed out: "
            f"{target} "
            f"(profile={profile})"
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"Nuclei scan failed: "
            f"{result.stderr}"
        )

    return parse_nuclei_jsonl(
        result.stdout
    )

def build_nuclei_evidence(
    data: dict,
    max_response_chars: int = 3000
) -> str:
    """
    从 Nuclei 原始 JSON 结果中构造适合保存和 AI 分析的证据。

    保留匹配位置和有限长度的 HTTP 响应，
    避免将过大的原始响应直接写入数据库和 Prompt。
    """

    matched_at = data.get("matched-at", "")
    response = data.get("response", "")

    evidence_parts = []

    if matched_at:
        evidence_parts.append(
            f"Matched At: {matched_at}"
        )

    if response:
        response = response.strip()

        if len(response) > max_response_chars:
            response = (
                response[:max_response_chars]
                + "\n...[response truncated]"
            )

        evidence_parts.append(
            "HTTP Response Evidence:\n"
            + response
        )

    return "\n\n".join(evidence_parts)


def parse_nuclei_jsonl(
    output: str
) -> list[dict]:
    """
    将 Nuclei JSONL 输出转换为 Python 字典列表，
    并对重复安全发现进行去重。
    """

    findings = []
    seen = set()

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        try:
            data = json.loads(line)

        except json.JSONDecodeError:
            continue

        info = data.get(
            "info",
            {}
        )

        classification = info.get(
        "classification",
        {}
        )

        cve_ids = classification.get(
            "cve-id",
            []
        ) or []

        cwe_ids = classification.get(
            "cwe-id",
            []
        ) or []

        # 某些情况下单个值可能不是 list，
        # 统一转换为 list，方便后续处理。
        if isinstance(cve_ids, str):
            cve_ids = [cve_ids]

        if isinstance(cwe_ids, str):
            cwe_ids = [cwe_ids]

        finding = {
            "template_id": data.get(
                "template-id",
                ""
            ),
            "cve_ids": cve_ids,

            "cwe_ids": cwe_ids,

            "name": info.get(
                "name",
                ""
            ),
            "severity": info.get(
                "severity",
                "unknown"
            ),
            "target": data.get(
                "host",
                ""
            ),
            "matched_at": data.get(
                "matched-at",
                ""
            ),
            "description": info.get(
                "description",
                ""
            ),
            "remediation": info.get(
                "remediation",
                ""
            ),
            "evidence": build_nuclei_evidence(data)
        }

        # 同一模板在同一位置产生的重复结果只保留一次
        dedup_key = (
            finding["template_id"],
            finding["matched_at"],
        )

        if dedup_key in seen:
            continue

        seen.add(dedup_key)
        findings.append(finding)

    return findings


if __name__ == "__main__":
    target = (
        "http://127.0.0.1:8000"
    )

    findings = run_nuclei(
        target=target,
        profile="fast"
    )

    print()
    print(
        f"Findings: {len(findings)}"
    )

    for finding in findings:
        print(
            finding
        )