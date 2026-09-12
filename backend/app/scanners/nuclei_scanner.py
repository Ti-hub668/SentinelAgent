import ipaddress
import json
import subprocess
from urllib.parse import urlparse


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


def run_nuclei(target: str) -> list[dict]:
    """
    调用 Nuclei 扫描 Web 服务。
    """

    validate_nuclei_target(target)

    command = [
        "nuclei",
        "-u",
        target,
        "-jsonl",
        "-silent",
        "-nc",
        "-duc",
        "-tags",
        "tech",
        "-timeout",
        "5",
        "-retries",
        "1",
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            shell=False
        )

    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"Nuclei scan timed out: {target}"
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"Nuclei scan failed: {result.stderr}"
        )

    return parse_nuclei_jsonl(result.stdout)


def parse_nuclei_jsonl(output: str) -> list[dict]:
    """
    将 Nuclei JSONL 输出转换为 Python 字典列表。
    """

    findings = []

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        info = data.get("info", {})

        findings.append({
            "template_id": data.get(
                "template-id",
                ""
            ),
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
            )
        })

    return findings