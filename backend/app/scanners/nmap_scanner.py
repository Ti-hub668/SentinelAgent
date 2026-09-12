import subprocess
import xml.etree.ElementTree as ET

from app.security.scope import validate_scan_target


def run_nmap(target: str) -> list[dict]:

    validate_scan_target(target)

    command = [
        "nmap",
        "-sV",
        "-oX",
        "-",
        target
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=300,
        shell=False
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Nmap scan failed: {result.stderr}"
        )

    return parse_nmap_xml(result.stdout)


def parse_nmap_xml(xml_data: str) -> list[dict]:

    root = ET.fromstring(xml_data)

    results = []

    for host in root.findall("host"):

        address_node = host.find("address")

        if address_node is None:
            continue

        host_address = address_node.get("addr")

        ports_node = host.find("ports")

        if ports_node is None:
            continue

        for port_node in ports_node.findall("port"):

            state_node = port_node.find("state")

            if state_node is None:
                continue

            if state_node.get("state") != "open":
                continue

            service_node = port_node.find("service")

            results.append({
                "host": host_address,
                "protocol": port_node.get("protocol"),
                "port": int(port_node.get("portid")),
                "service": (
                    service_node.get("name", "")
                    if service_node is not None
                    else ""
                ),
                "product": (
                    service_node.get("product", "")
                    if service_node is not None
                    else ""
                ),
                "version": (
                    service_node.get("version", "")
                    if service_node is not None
                    else ""
                )
            })

    return results