from datetime import date, datetime, time, timezone

from sqlalchemy import Date, DateTime, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    interview_date: Mapped[date] = mapped_column(Date, nullable=False)
    interview_time: Mapped[time] = mapped_column(Time, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )