from google import genai
from google.genai import types

from app.core.config import settings


EMBEDDING_DIMENSIONS = 3072

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client

    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)

    return _client


def _embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
    if not texts:
        return []

    if any(not text.strip() for text in texts):
        raise ValueError("Text to embed cannot be empty.")

    response = _get_client().models.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )

    embeddings = response.embeddings
    if embeddings is None or len(embeddings) != len(texts):
        raise RuntimeError("Gemini returned an unexpected number of embeddings.")

    vectors: list[list[float]] = []
    for embedding in embeddings:
        values = embedding.values
        if values is None or len(values) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Expected an embedding with {EMBEDDING_DIMENSIONS} dimensions."
            )
        vectors.append([float(value) for value in values])

    return vectors


def embed_documents(texts: list[str]) -> list[list[float]]:
    return _embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    vectors = _embed_texts([text], task_type="RETRIEVAL_QUERY")
    return vectors[0]