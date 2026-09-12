def build_web_targets(ports: list[dict]) -> list[str]:
    """
    根据 Nmap 发现的开放端口生成 Web URL。
    开发阶段只扫描明确的常见 Web 端口。
    """

    targets = []

    allowed_web_ports = {
        80: "http",
        443: "https",
        8000: "http",
        8080: "http",
        8443: "https",
    }

    for item in ports:
        host = item["host"]
        port = item["port"]

        if port not in allowed_web_ports:
            continue

        scheme = allowed_web_ports[port]

        if port == 80:
            url = f"http://{host}"

        elif port == 443:
            url = f"https://{host}"

        else:
            url = f"{scheme}://{host}:{port}"

        targets.append(url)

    return list(dict.fromkeys(targets))