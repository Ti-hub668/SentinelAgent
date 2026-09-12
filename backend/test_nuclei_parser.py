from app.scanners.nuclei_scanner import parse_nuclei_jsonl


sample = """
{"template-id":"test-template","info":{"name":"Test Finding","severity":"medium","description":"This is a test finding.","remediation":"Update the affected service."},"host":"http://127.0.0.1:8000","matched-at":"http://127.0.0.1:8000/test"}
"""


results = parse_nuclei_jsonl(sample)


for result in results:
    print(result)