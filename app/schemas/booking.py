from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BookingDraft(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    interview_date: date | None = None
    interview_time: time | None = None


class BookingSessionState(BaseModel):
    draft: BookingDraft = Field(default_factory=BookingDraft)
    awaiting_confirmation: bool = False


class BookingTurnExtraction(BaseModel):
    intent: Literal["book", "confirm", "cancel", "other"]
    name: str | None = None
    email: str | None = None
    interview_date: str | None = None
    interview_time: str | None = None


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    interview_date: date
    interview_time: time
    created_at: datetime