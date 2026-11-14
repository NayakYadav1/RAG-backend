from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.document import ChunkingStrategy, DocumentUploadResponse
from app.services.document_ingestion import (
    DocumentProcessingError,
    ingest_document,
)


router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
def upload_document(
    file: Annotated[UploadFile, File(...)],
    chunking_strategy: Annotated[ChunkingStrategy, Form(...)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    try:
        file_bytes = file.file.read()
        document = ingest_document(
            db=db,
            filename=file.filename,
            file_bytes=file_bytes,
            strategy=chunking_strategy,
        )
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DocumentUploadResponse.model_validate(document)