from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Event:
    """
    Immutable runtime event.

    Event represents an observable fact that occurred during
    runtime execution.
    """

    type: str

    source: str

    # trace_id: str

    payload: dict[str, Any] = field(default_factory=dict)

    id: str = field(default_factory=lambda: str(uuid4()))

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )