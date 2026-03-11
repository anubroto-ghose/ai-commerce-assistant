import time
import uuid
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ChatSession:
    session_id: str
    created_at: float
    last_seen: float
    messages: list[dict] = field(default_factory=list)


class InMemorySessionService:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, ChatSession] = {}
        self._lock = Lock()

    def ensure_session(self, session_id: str | None) -> ChatSession:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                session.last_seen = now
                return session

            new_id = session_id or str(uuid.uuid4())
            session = ChatSession(session_id=new_id, created_at=now, last_seen=now)
            self._sessions[new_id] = session
            return session

    def append_message(self, session_id: str, role: str, content: str) -> None:
        now = time.time()
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return
            session.last_seen = now
            session.messages.append({"role": role, "content": content, "ts": now})
            if len(session.messages) > 40:
                session.messages = session.messages[-40:]

    def get_recent_messages(self, session_id: str, limit: int = 12) -> list[dict]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            session = self._sessions.get(session_id)
            if not session:
                return []
            session.last_seen = now
            return session.messages[-limit:]

    def _cleanup(self, now: float) -> None:
        stale = [
            session_id
            for session_id, session in self._sessions.items()
            if (now - session.last_seen) > self.ttl_seconds
        ]
        for session_id in stale:
            self._sessions.pop(session_id, None)
