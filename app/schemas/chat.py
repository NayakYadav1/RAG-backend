from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=10_000)


class ChatResponse(BaseModel):
    session_id: str
    answer: str