from app.scanners.web_discovery import build_web_targets


ports = [
    {
        "host": "127.0.0.1",
        "protocol": "tcp",
        "port": 8000,
        "service": "http",
        "product": "uvicorn",
        "version": ""
    },
    {
        "host": "127.0.0.1",
        "protocol": "tcp",
        "port": 3306,
        "service": "mysql",
        "product": "MySQL",
        "version": "8.0"
    }
]


targets = build_web_targets(ports)

print(targets)