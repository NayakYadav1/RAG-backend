import json
import re
from functools import lru_cache

from google import genai
from google.genai import types
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.booking import Booking
from app.schemas.booking import (
    BookingDraft,
    BookingSessionState,
    BookingTurnExtraction,
)
from app.services.conversation import get_redis_client


_BOOKING_KEY_PREFIX = "booking:session:"


@lru_cache(maxsize=1)
def _get_gemini_client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _booking_key(session_id: str) -> str:
    return f"{_BOOKING_KEY_PREFIX}{session_id}"

def _looks_like_booking_request(message: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", message.casefold())
    booking_terms = {
        "appointment",
        "book",
        "booking",
        "interview",
        "reserve",
        "schedule",
    }
    return bool(set(normalized.split()) & booking_terms)


def _get_booking_state(session_id: str) -> BookingSessionState | None:
    stored_state = get_redis_client().get(_booking_key(session_id))
    if stored_state is None:
        return None

    try:
        return BookingSessionState.model_validate_json(stored_state)
    except ValidationError as exc:
        raise RuntimeError("Stored booking draft is invalid.") from exc


def _save_booking_state(
    session_id: str,
    state: BookingSessionState,
) -> None:
    get_redis_client().set(
        _booking_key(session_id),
        state.model_dump_json(),
        ex=settings.CHAT_HISTORY_TTL_SECONDS,
    )


def _delete_booking_state(session_id: str) -> None:
    get_redis_client().delete(_booking_key(session_id))


def _extract_booking_turn(
    message: str,
    state: BookingSessionState | None,
) -> BookingTurnExtraction:
    current_state = (
        state.model_dump_json()
        if state is not None
        else "There is no active booking draft."
    )
    prompt = f"""
Classify the user's latest message and extract only details the user stated.

Return intent "book" when they ask to book an interview or provide/correct
booking details for an active draft.
Return "confirm" only for an explicit yes to the complete booking summary
when awaiting_confirmation is true.
Return "cancel" only when they explicitly cancel or decline the booking.
Otherwise return "other".

Never invent missing details. Convert an explicitly stated date to YYYY-MM-DD
and time to 24-hour HH:MM. If a date or time is ambiguous, return null for it.
For an active draft, treat a message containing a requested detail as "book".
Return only the requested structured fields.

Active booking state:
{current_state}

Latest user message as a JSON string:
{json.dumps(message)}
""".strip()

    response = _get_gemini_client().models.generate_content(
        model=settings.GEMINI_CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BookingTurnExtraction,
            temperature=0,
        ),
    )

    if response.text is None or not response.text.strip():
        raise RuntimeError("Gemini returned an empty booking extraction.")

    return BookingTurnExtraction.model_validate_json(response.text)


def _next_missing_question(draft: BookingDraft) -> str | None:
    questions = (
        ("name", "What name should I use for the interview booking?"),
        ("email", "What email address should I use?"),
        (
            "interview_date",
            "What date works for you? Please use YYYY-MM-DD.",
        ),
        (
            "interview_time",
            "What time works for you? Please use 24-hour time, such as 14:30.",
        ),
    )

    for field_name, question in questions:
        if getattr(draft, field_name) is None:
            return question

    return None


def process_booking_turn(
    db: Session,
    session_id: str,
    message: str,
) -> str | None:
    state = _get_booking_state(session_id)
    if state is None and not _looks_like_booking_request(message):
        return None

    extraction = _extract_booking_turn(message, state)

    if state is None and extraction.intent != "book":
        return None

    if extraction.intent == "cancel":
        if state is None:
            return None
        _delete_booking_state(session_id)
        return "Okay, I canceled that interview booking draft."

    if state is not None and extraction.intent == "other":
        return None

    if (
        state is not None
        and state.awaiting_confirmation
        and extraction.intent == "confirm"
    ):
        draft = state.draft
        if _next_missing_question(draft) is not None:
            raise RuntimeError("Cannot confirm an incomplete booking.")

        booking = Booking(
            name=draft.name,
            email=str(draft.email),
            interview_date=draft.interview_date,
            interview_time=draft.interview_time,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        _delete_booking_state(session_id)

        return (
            f"Your interview booking is confirmed (booking ID {booking.id}) "
            f"for {booking.interview_date.isoformat()} at "
            f"{booking.interview_time.strftime('%H:%M')} local time."
        )

    if state is None:
        state = BookingSessionState()

    draft_values = state.draft.model_dump()
    updates = {
        "name": extraction.name,
        "email": extraction.email,
        "interview_date": extraction.interview_date,
        "interview_time": extraction.interview_time,
    }

    invalid_questions = {
        "name": "What name should I use? Please provide a non-empty name.",
        "email": "That email doesn't look valid. Please provide a valid email address.",
        "interview_date": "I couldn't read that date. Please use YYYY-MM-DD.",
        "interview_time": "I couldn't read that time. Please use 24-hour time, such as 14:30.",
    }

    for field_name, value in updates.items():
        if value is None:
            continue

        cleaned_value = value.strip()
        if not cleaned_value:
            continue

        try:
            validated_draft = BookingDraft.model_validate(
                {**draft_values, field_name: cleaned_value}
            )
        except ValidationError:
            state = BookingSessionState(
                draft=BookingDraft.model_validate(draft_values),
                awaiting_confirmation=False,
            )
            _save_booking_state(session_id, state)
            return invalid_questions[field_name]

        draft_values[field_name] = getattr(validated_draft, field_name)

    draft = BookingDraft.model_validate(draft_values)
    state = BookingSessionState(draft=draft, awaiting_confirmation=False)

    missing_question = _next_missing_question(draft)
    if missing_question is not None:
        _save_booking_state(session_id, state)
        return missing_question

    state.awaiting_confirmation = True
    _save_booking_state(session_id, state)

    return (
        "Please confirm this interview booking: "
        f"{draft.name}, {draft.email}, "
        f"{draft.interview_date.isoformat()} at "
        f"{draft.interview_time.strftime('%H:%M')} local time. "
        "Reply yes to confirm, provide a correction, or say cancel."
    )