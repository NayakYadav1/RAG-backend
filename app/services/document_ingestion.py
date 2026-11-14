from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.orm import Session

from app.models.document import Document
from app.schemas.document import ChunkingStrategy
from app.services.chunking import chunk_text
from app.services.embeddings import embed_documents
from app.services.vector_store import upsert_chunks


class DocumentProcessingError(ValueError):
    pass


def extract_document_text(filename: str, file_bytes: bytes) -> str:
    if not file_bytes:
        raise DocumentProcessingError("The uploaded file is empty.")

    extension = Path(filename).suffix.lower()

    if extension == ".txt":
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentProcessingError(
                "Text files must use UTF-8 encoding."
            ) from exc
    elif extension == ".pdf":
        try:
            reader = PdfReader(BytesIO(file_bytes))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except PdfReadError as exc:
            raise DocumentProcessingError(
                "The PDF file is invalid or unreadable."
            ) from exc
    else:
        raise DocumentProcessingError("Only .pdf and .txt files are supported.")

    cleaned_text = text.strip()
    if not cleaned_text:
        raise DocumentProcessingError(
            "No readable text was found in the document."
        )

    return cleaned_text


def process_document(
    filename: str,
    file_bytes: bytes,
    strategy: ChunkingStrategy,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:
    text = extract_document_text(filename, file_bytes)
    return chunk_text(
        text=text,
        strategy=strategy,
        chunk_size=chunk_size,
        overlap=overlap,
    )


def ingest_document(
    db: Session,
    filename: str,
    file_bytes: bytes,
    strategy: ChunkingStrategy,
) -> Document:
    chunks = process_document(filename, file_bytes, strategy)
    embeddings = embed_documents(chunks)

    document = Document(
        filename=filename,
        chunking_strategy=strategy.value,
        chunk_count=len(chunks),
    )

    with db.begin():
        db.add(document)
        db.flush()

        upsert_chunks(
            document_id=document.id,
            filename=filename,
            chunks=chunks,
            embeddings=embeddings,
            strategy=strategy,
        )

    db.refresh(document)
    return document