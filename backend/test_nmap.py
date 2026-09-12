from app.scanners.nmap_scanner import run_nmap


results = run_nmap("127.0.0.1")


for item in results:
    print(item)