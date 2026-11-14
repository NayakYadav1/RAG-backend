from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.booking import process_booking_turn
from app.services.conversation import (
    append_conversation_turn,
    get_conversation_history,
)
from app.services.rag import answer_question


router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ChatResponse:
    session_id = request.session_id or uuid4().hex

    try:
        history = get_conversation_history(session_id)
        answer = process_booking_turn(
            db=db,
            session_id=session_id,
            message=request.message,
        )

        if answer is None:
            answer = answer_question(
                question=request.message,
                conversation_history=history,
            )

        append_conversation_turn(
            session_id=session_id,
            user_message=request.message,
            assistant_message=answer,
        )
    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="Conversation or booking storage is unavailable.",
        ) from exc

    return ChatResponse(session_id=session_id, answer=answer)