def build_web_targets(ports: list[dict]) -> list[str]:
    """
    根据 Nmap 扫描结果识别可能的 Web 服务，并生成对应 URL。

    优先根据 Nmap 的 service/product 信息识别 Web 服务，
    常见 Web 端口作为补充判断。
    """

    targets = []

    # 常见 Web 端口，作为服务识别失败时的补充
    known_web_ports = {
        80: "http",
        443: "https",
        3000: "http",
        5000: "http",
        8000: "http",
        8080: "http",
        8443: "https",
        8888: "http",
    }

    for item in ports:
        host = item["host"]
        port = item["port"]

        service = (item.get("service") or "").lower()
        product = (item.get("product") or "").lower()

        # ---------- 1. 根据服务信息判断 ----------

        is_http_service = (
            service == "http"
            or service.startswith("http-")
            or "http" in product
            or "uvicorn" in product
        )

        is_https_service = (
            service == "https"
            or service.startswith("https-")
            or "ssl/http" in service
            or "https" in product
        )

        # ---------- 2. 确定协议 ----------

        if is_https_service:
            scheme = "https"

        elif is_http_service:
            scheme = "http"

        elif port in known_web_ports:
            scheme = known_web_ports[port]

        else:
            continue

        # ---------- 3. 生成 URL ----------

        if port == 80 and scheme == "http":
            url = f"http://{host}"

        elif port == 443 and scheme == "https":
            url = f"https://{host}"

        else:
            url = f"{scheme}://{host}:{port}"

        targets.append(url)

    # 去重并保持原顺序
    return list(dict.fromkeys(targets))