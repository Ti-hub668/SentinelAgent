import json
import urllib.request
from typing import Any


OLLAMA_BASE_URL = (
    "http://127.0.0.1:11434"
)

DEFAULT_EMBEDDING_MODEL = (
    "nomic-embed-text"
)


def embed_texts(
    texts: list[str],
    model: str = DEFAULT_EMBEDDING_MODEL,
    timeout: float = 120.0,
) -> list[list[float]]:
    """
    Generate embeddings for multiple texts
    in one Ollama /api/embed request.
    """

    if not texts:
        return []

    normalized_texts = []

    for text in texts:
        value = str(text).strip()

        if not value:
            raise ValueError(
                "Embedding text cannot "
                "be empty."
            )

        normalized_texts.append(
            value
        )

    payload = {
        "model": model,
        "input": normalized_texts,
    }

    request = urllib.request.Request(
        url=(
            f"{OLLAMA_BASE_URL}"
            "/api/embed"
        ),
        data=json.dumps(
            payload
        ).encode(
            "utf-8"
        ),
        headers={
            "Content-Type":
                "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            result: dict[
                str,
                Any,
            ] = json.loads(
                response
                .read()
                .decode(
                    "utf-8"
                )
            )

    except Exception as exc:
        raise RuntimeError(
            "Failed to generate "
            f"embeddings: {exc}"
        ) from exc

    embeddings = result.get(
        "embeddings"
    )

    if not embeddings:
        raise RuntimeError(
            "Ollama response does not "
            "contain embeddings."
        )

    if (
        len(embeddings)
        != len(normalized_texts)
    ):
        raise RuntimeError(
            "Embedding count mismatch: "
            f"requested "
            f"{len(normalized_texts)}, "
            f"received "
            f"{len(embeddings)}."
        )

    return embeddings


def embed_text(
    text: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
    timeout: float = 120.0,
) -> list[float]:
    """
    Generate one embedding while sharing
    the same batch implementation.
    """

    embeddings = embed_texts(
        [text],
        model=model,
        timeout=timeout,
    )

    return embeddings[0]