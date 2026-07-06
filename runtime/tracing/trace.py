from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from runtime.tracing.span import Span


@dataclass(slots=True, kw_only=True)
class Trace:
    """
    Represents a complete execution trace.

    Trace is the aggregate root of the tracing system.

    It owns all spans created during one runtime execution.
    """

    trace_id: str

    root_span_id: str | None = None

    start_time: datetime

    end_time: datetime | None = None

    _spans: Dict[str, Span] = field(default_factory=dict)

    def add_span(self, span: Span) -> None:
        """
        Register a span into this trace.

        Args:
            span: Span instance to be added.
        """
        self._spans[span.span_id] = span

        if self.root_span_id is None:
            self.root_span_id = span.span_id

    def has_span(self, span_id: str) -> bool:
        """Return whether the span exists."""
        return span_id in self._spans

    def get_span(self, span_id: str) -> Optional[Span]:
        """
        Retrieve a span by its id.

        Args:
            span_id: span identifier

        Returns:
            Span or None if not found.
        """
        return self._spans.get(span_id)

    def all_spans(self) -> list[Span]:
        """
        Return all spans in this trace.

        Returns:
            List of spans (unordered).
        """
        return list(self._spans.values())

    @property
    def span_count(self) -> int:
        return len(self._spans)

    @property
    def duration_ms(self) -> float | None:
        """
        Total trace duration in milliseconds.
        """
        if self.end_time is None:
            return None

        return (self.end_time - self.start_time).total_seconds() * 1000
