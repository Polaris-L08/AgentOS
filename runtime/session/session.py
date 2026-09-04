from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


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