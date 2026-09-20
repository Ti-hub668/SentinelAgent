# SentinelAgent Security Knowledge Base

SentinelAgent Security Knowledge Base 用于为 RAG 安全分析模块提供结构化安全知识。

知识库的目标不是替代当前 Finding 的 Evidence，而是为 LLM 提供安全语义、常见配置、暴露类型以及证据判断要求等辅助上下文。

在 AI 风险分析过程中，应始终遵循：

Finding Evidence > Retrieved Knowledge

检索到的知识不能作为当前目标存在漏洞的直接证据。


## 1. Directory Structure

knowledge/
├── README.md
├── raw/
│   └── web_security_basics.json
├── processed/
└── vector_store/
    └── security_index.json

### raw

保存原始结构化安全知识。

### processed

用于保存经过清洗、标准化或 Chunking 后的中间数据。

### vector_store

保存 Embedding 后生成的本地向量索引。


## 2. Document Schema

每条安全知识统一使用以下结构：

```json
{
  "id": "web_headers_001",
  "title": "Missing HTTP Security Headers",
  "content": "Security knowledge content...",
  "source": "sentinelagent_internal",
  "category": "security_misconfiguration",
  "metadata": {
    "technology": "http",
    "topic": "security_headers",
    "tags": [
      "http",
      "headers",
      "misconfiguration"
    ]
  }
}