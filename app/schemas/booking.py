from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BookingDraft(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    interview_date: date | None = None
    interview_time: time | None = None


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    interview_date: date
    interview_time: time
    created_at: datetime