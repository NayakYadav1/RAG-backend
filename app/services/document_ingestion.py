from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from app.schemas.document import ChunkingStrategy
from app.services.chunking import chunk_text


def extract_document_text(filename: str, file_bytes: bytes) -> str:
    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    extension = Path(filename).suffix.lower()

    if extension == ".txt":
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must use UTF-8 encoding.") from exc
    elif extension == ".pdf":
        reader = PdfReader(BytesIO(file_bytes))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise ValueError("Only .pdf and .txt files are supported.")

    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("No readable text was found in the document.")

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