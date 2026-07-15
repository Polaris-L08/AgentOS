from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Event:
    """
    Immutable runtime events.

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

    # tracing metadata

    trace_id: str | None = None

    span_id: str | None = None

    # multi-agent

    # source 是事件产生来源组件，如：tool_executor/middleware/checkpoint_manager
    # sender 是Agent通信中的发送者，如：research_agent
    sender: str | None = None

    receiver: str | None = None

    correlation_id: str | None = None