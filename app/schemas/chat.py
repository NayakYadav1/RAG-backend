from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=10_000)

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("session_id cannot contain only whitespace.")

        return cleaned_value

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("message cannot contain only whitespace.")

        return cleaned_value


class ChatResponse(BaseModel):
    session_id: str
    answer: str