from __future__ import annotations

import uuid

from runtime.session.session import Session


class SessionManager:
    """
    Runtime manager responsible for Session creation and lookup.

    This is intentionally an in-memory manager.

    It is NOT a persistence repository and does not define a database
    abstraction.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create_session(
        self,
        metadata: dict | None = None,
    ) -> Session:
        """
        Create and register a new Session.
        """

        session = Session(
            session_id=str(uuid.uuid4()),
            metadata=dict(metadata or {}),
        )

        self._sessions[session.session_id] = session

        return session

    def get_session(
        self,
        session_id: str,
    ) -> Session:
        """
        Return an existing Session.
        """

        try:
            return self._sessions[session_id]
        except KeyError:
            raise KeyError(
                f"Session not found: {session_id}"
            ) from None

    def has_session(
        self,
        session_id: str,
    ) -> bool:
        """
        Return whether a Session exists.
        """

        return session_id in self._sessions

    def delete_session(
        self,
        session_id: str,
    ) -> None:
        """
        Delete an existing Session.
        """

        if session_id not in self._sessions:
            raise KeyError(
                f"Session not found: {session_id}"
            )

        del self._sessions[session_id]