from app.scanners.nuclei_scanner import run_nuclei


target = "http://127.0.0.1:8000"

print(f"正在扫描：{target}")

results = run_nuclei(target)

print(f"扫描完成，发现 {len(results)} 条结果")

for item in results:
    print(item)