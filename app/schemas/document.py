from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ChunkingStrategy(str, Enum):
    FIXED_SIZE = "fixed_size"
    RECURSIVE_PARAGRAPH = "recursive_paragraph"


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    chunking_strategy: ChunkingStrategy
    chunk_count: int
    uploaded_at: datetime