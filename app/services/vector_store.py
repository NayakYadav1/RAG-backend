from functools import lru_cache
from uuid import uuid4
from typing import TypedDict

from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.schemas.document import ChunkingStrategy
from app.services.embeddings import EMBEDDING_DIMENSIONS


class RetrievedChunk(TypedDict):
    text: str
    document_id: int
    filename: str
    chunk_index: int
    chunking_strategy: str
    score: float


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)


def ensure_collection() -> None:
    client = get_qdrant_client()

    if not client.collection_exists(settings.QDRANT_COLLECTION_NAME):
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=models.Distance.COSINE,
            ),
        )


def upsert_chunks(
    document_id: int,
    filename: str,
    chunks: list[str],
    embeddings: list[list[float]],
    strategy: ChunkingStrategy,
) -> list[str]:
    if len(chunks) != len(embeddings):
        raise ValueError("Each chunk must have exactly one embedding.")

    if not chunks:
        return []

    for embedding in embeddings:
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Every embedding must have {EMBEDDING_DIMENSIONS} dimensions."
            )

    ensure_collection()

    point_ids = [str(uuid4()) for _ in chunks]
    points = [
        models.PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "text": chunk,
                "document_id": document_id,
                "filename": filename,
                "chunk_index": index,
                "chunking_strategy": strategy.value,
            },
        )
        for index, (point_id, chunk, embedding) in enumerate(
            zip(point_ids, chunks, embeddings, strict=True)
        )
    ]

    get_qdrant_client().upsert(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points=points,
        wait=True,
    )
    return point_ids


def search_chunks(
    query_embedding: list[float],
    limit: int = 5,
) -> list[RetrievedChunk]:
    if len(query_embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"The query embedding must have {EMBEDDING_DIMENSIONS} dimensions."
        )
    if limit < 1:
        raise ValueError("limit must be at least 1.")

    ensure_collection()

    response = get_qdrant_client().query_points(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query=query_embedding,
        limit=limit,
        with_payload=True,
    )

    results: list[RetrievedChunk] = []
    for point in response.points:
        payload = point.payload
        if payload is None:
            raise RuntimeError("Qdrant returned a point without a payload.")

        text = payload.get("text")
        document_id = payload.get("document_id")
        filename = payload.get("filename")
        chunk_index = payload.get("chunk_index")
        chunking_strategy = payload.get("chunking_strategy")

        if (
            not isinstance(text, str)
            or not isinstance(document_id, int)
            or not isinstance(filename, str)
            or not isinstance(chunk_index, int)
            or not isinstance(chunking_strategy, str)
            or point.score is None
        ):
            raise RuntimeError("Qdrant returned a point with invalid data.")

        results.append(
            {
                "text": text,
                "document_id": document_id,
                "filename": filename,
                "chunk_index": chunk_index,
                "chunking_strategy": chunking_strategy,
                "score": float(point.score),
            }
        )

    return results