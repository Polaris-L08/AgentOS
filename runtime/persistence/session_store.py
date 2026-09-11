from __future__ import annotations

from typing import Protocol

from runtime.session.session_state import SessionState


class SessionStore(Protocol):
    """
    Persistence contract for durable Session state.

    Implementations may use an in-memory store, PostgreSQL, or another
    durable storage backend.
    """

    async def save(self, state: SessionState) -> None:
        """
        Persist a SessionState.

        If a Session with the same session_id already exists, the
        implementation should replace its durable state.
        """
        ...

    async def load(self, session_id: str) -> SessionState | None:
        """
        Load a SessionState by session_id.

        Returns None when the Session does not exist.
        """
        ...

    async def delete(self, session_id: str) -> None:
        """
        Delete a SessionState by session_id.

        Deleting a non-existent Session should be safe.
        """
        ...