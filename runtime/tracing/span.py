from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SpanStatus(str, Enum):
    """Execution status of a span."""

    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"

@dataclass(slots=True, kw_only=True)
class Span:
    """
    Represents one execution span within a trace.

    Span is a runtime data model. It records the execution
    information of a single runtime operation.

    Lifecycle:
        RUNNING -> SUCCESS
        RUNNING -> ERROR
    """

    span_id: str

    trace_id: str

    parent_span_id: str | None = None

    name: str

    start_time: datetime

    end_time: datetime | None

    status: SpanStatus = SpanStatus.RUNNING

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        """
        Returns execution duration in milliseconds.

        Returns:
            None if the span has not finished.
        """

        if self.end_time is None:
            return None

        return (self.end_time - self.start_time).total_seconds() * 1000
