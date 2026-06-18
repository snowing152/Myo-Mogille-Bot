from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


def normalize(text: str) -> str:
    return text.lower().replace("ё", "е").strip()


def is_trigger(text: str, phrases: tuple[str, ...]) -> bool:
    norm = normalize(text)
    return any(normalize(phrase) in norm for phrase in phrases)


class SessionState(Enum):
    IDLE = "idle"
    COLLECTING = "collecting"


@dataclass
class Session:
    chat_id: int
    state: SessionState = SessionState.IDLE
    messages: list[str] = field(default_factory=list)
    started_at: float = 0.0
    prompt_message_id: int | None = None

    def add_message(self, text: str) -> None:
        cleaned = text.strip()
        if cleaned:
            self.messages.append(cleaned)


class SessionStore:
    """In-memory per-chat sessions with lazy expiry."""

    def __init__(self, timeout_min: int, now: Callable[[], float] = time.monotonic) -> None:
        self._timeout_s = timeout_min * 60
        self._now = now
        self._sessions: dict[int, Session] = {}

    def start(self, chat_id: int) -> Session:
        session = Session(
            chat_id=chat_id,
            state=SessionState.COLLECTING,
            started_at=self._now(),
        )
        self._sessions[chat_id] = session
        return session

    def get_active(self, chat_id: int) -> Session | None:
        session = self._sessions.get(chat_id)
        if session is None or session.state != SessionState.COLLECTING:
            return None
        if self._now() - session.started_at > self._timeout_s:
            self.end(chat_id)
            return None
        return session

    def end(self, chat_id: int) -> None:
        self._sessions.pop(chat_id, None)
