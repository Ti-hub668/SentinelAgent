import json

from app.ai.risk_analyst import analyze_finding
from app.rag.context_builder import build_rag_context
from app.rag.query_builder import build_finding_query
from app.rag.retriever import SecurityKnowledgeRetriever
from app.schemas.ai_analysis import AIAnalysisInput


# ==================================================
# 1. 读取 real_002
# ==================================================

with open(
    "evals/real_findings_labeled_v1.json",
    "r",
    encoding="utf-8",
) as file:
    dataset = json.load(file)


case = next(
    item
    for item in dataset
    if item["id"] == "real_002"
)


print("=== TEST CASE ===")
print("Case ID:", case["id"])
print("Title:", case["title"])
print("Expected Verdict:", case["expected_verdict"])


# ==================================================
# 2. 转换为 AIAnalysisInput
# ==================================================

finding = AIAnalysisInput(
    finding_id=case["finding_id"],
    source=case["source"],
    finding_type=case["finding_type"],
    title=case["title"],
    severity=case["severity"],
    target=case["target"],
    description=case.get("description"),
    evidence=case.get("evidence"),
    remediation=case.get("remediation"),
    risk_score=case["risk_score"],
    risk_level=case["risk_level"],
    risk_reason=case.get("risk_reason"),
)


# ==================================================
# 3. 构造 RAG Query
# ==================================================

query = build_finding_query(finding)

print("\n=== RAG QUERY ===")
print(query)


# ==================================================
# 4. Retrieval
# ==================================================

retriever = SecurityKnowledgeRetriever()

results = retriever.retrieve(
    query=query,
    top_k=3,
)


print("\n=== RETRIEVAL RESULTS ===")

for result in results:
    print(
        f"{result.score:.4f} - "
        f"{result.document.title}"
    )


# ==================================================
# 5. 构造 RAG Context
# ==================================================

rag_context = build_rag_context(results)

print("\n=== RAG CONTEXT ===")
print(rag_context)


# ==================================================
# 6. No-RAG
# ==================================================

no_rag_analysis = analyze_finding(
    finding,
)

print("\n=== NO-RAG ANALYSIS ===")
print(
    no_rag_analysis.model_dump_json(
        indent=2,
    )
)


# ==================================================
# 7. RAG
# ==================================================

rag_analysis = analyze_finding(
    finding,
    rag_context=rag_context,
)

print("\n=== RAG ANALYSIS ===")
print(
    rag_analysis.model_dump_json(
        indent=2,
    )
)


# ==================================================
# 8. 对比 Ground Truth
# ==================================================

expected = case["expected_verdict"]

print("\n=== COMPARISON ===")
print("Expected:", expected)
print("No-RAG :", no_rag_analysis.verdict)
print("RAG    :", rag_analysis.verdict)

print(
    "No-RAG Correct:",
    no_rag_analysis.verdict == expected,
)

print(
    "RAG Correct:",
    rag_analysis.verdict == expected,
)