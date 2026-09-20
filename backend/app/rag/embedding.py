import json
import urllib.request
from typing import Any


OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"


def embed_text(
    text: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> list[float]:
    """
    使用本地 Ollama Embedding 模型将文本转换为向量。
    """

    text = text.strip()

    if not text:
        raise ValueError("Embedding text cannot be empty.")

    payload = {
        "model": model,
        "input": text,
    }

    request = urllib.request.Request(
        url=f"{OLLAMA_BASE_URL}/api/embed",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:
            result: dict[str, Any] = json.loads(
                response.read().decode("utf-8")
            )

    except Exception as exc:
        raise RuntimeError(
            f"Failed to generate embedding: {exc}"
        ) from exc

    embeddings = result.get("embeddings")

    if not embeddings:
        raise RuntimeError(
            "Ollama response does not contain embeddings."
        )

    return embeddings[0]