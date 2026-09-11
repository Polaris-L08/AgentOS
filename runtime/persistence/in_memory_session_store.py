from __future__ import annotations

from copy import deepcopy

from runtime.persistence.session_store import SessionStore
from runtime.session.session_state import SessionState


class InMemorySessionStore(SessionStore):
    """
    In-memory implementation of SessionStore.

    This implementation is intended for local execution, testing, and
    as a reference implementation of the SessionStore contract.

    It does not provide durability across process restarts.
    """

    def __init__(self) -> None:
        self._states: dict[str, SessionState] = {}

    async def save(self, state: SessionState) -> None:
        """
        Persist a SessionState in memory.

        Existing state with the same session_id is replaced.
        """
        self._states[state.session_id] = deepcopy(state)

    async def load(self, session_id: str) -> SessionState | None:
        """
        Load a SessionState by session_id.

        Returns None when the Session does not exist.
        """
        state = self._states.get(session_id)

        if state is None:
            return None

        return deepcopy(state)

    async def delete(self, session_id: str) -> None:
        """
        Delete a SessionState by session_id.

        Deleting a non-existent Session is safe.
        """
        self._states.pop(session_id, None)