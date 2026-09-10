from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from runtime.session.session_state import SessionState


@dataclass(slots=True)
class Session:
    """
    Logical conversation/session boundary.

    A Session groups multiple executions that belong to the same
    logical interaction.

    Session does not own:

    - RuntimeContext
    - AgentExecutionContext
    - AgentContext
    - MemoryRuntime
    - ExecutionRuntime

    Those objects belong to different lifecycle boundaries.
    """

    session_id: str

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def snapshot(self) -> SessionState:
        """
        Create a durable representation of this Session.
        """
        return SessionState(
            session_id=self.session_id,
            created_at=self.created_at,
            metadata=dict(self.metadata),
        )

    @classmethod
    def from_state(cls, state: SessionState) -> Session:
        """
        Reconstruct a live Session object from durable state.
        """
        return cls(
            session_id=state.session_id,
            created_at=state.created_at,
            metadata=dict(state.metadata),
        )