from app.schemas.messages import SESSION_ID_PATTERN


class SessionManager:
    def __init__(self) -> None:
        self._sessions: set[str] = set()

    def session_exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    async def create_session(self, session_id: str) -> None:
        if not SESSION_ID_PATTERN.match(session_id):
            raise ValueError("Invalid session_id format")

        if session_id in self._sessions:
            raise FileExistsError(f"Session {session_id} already exists")

        self._sessions.add(session_id)
