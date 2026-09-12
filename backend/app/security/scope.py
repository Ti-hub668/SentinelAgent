import ipaddress


def validate_scan_target(target: str) -> bool:
    try:
        ip = ipaddress.ip_address(target)
    except ValueError:
        raise ValueError("当前版本仅支持 IP 地址")

    if ip.is_loopback or ip.is_private:
        return True

    raise ValueError(
        "开发环境仅允许扫描本机或私有网络中的授权资产"
    )