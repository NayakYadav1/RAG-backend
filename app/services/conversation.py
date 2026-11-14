import json
from functools import lru_cache
from typing import Literal, TypedDict

from redis import Redis

from app.core.config import settings


class ChatHistoryMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


MAX_HISTORY_MESSAGES = 20
_KEY_PREFIX = "chat:session:"


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    return Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def _history_key(session_id: str) -> str:
    return f"{_KEY_PREFIX}{session_id}"


def get_conversation_history(session_id: str) -> list[ChatHistoryMessage]:
    stored_messages = get_redis_client().lrange(
        _history_key(session_id),
        0,
        -1,
    )

    history: list[ChatHistoryMessage] = []
    for stored_message in stored_messages:
        try:
            item = json.loads(stored_message)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Stored chat history contains invalid JSON.") from exc

        if not isinstance(item, dict):
            raise RuntimeError("Stored chat history contains an invalid message.")

        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            raise RuntimeError("Stored chat history contains an invalid message.")

        history.append({"role": role, "content": content})

    return history


def append_conversation_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
) -> None:
    key = _history_key(session_id)
    client = get_redis_client()

    with client.pipeline(transaction=True) as pipeline:
        pipeline.rpush(
            key,
            json.dumps({"role": "user", "content": user_message}),
            json.dumps({"role": "assistant", "content": assistant_message}),
        )
        pipeline.ltrim(key, -MAX_HISTORY_MESSAGES, -1)
        pipeline.expire(key, settings.CHAT_HISTORY_TTL_SECONDS)
        pipeline.execute()