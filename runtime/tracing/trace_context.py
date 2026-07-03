from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from runtime.tracing.span import Span, SpanStatus
from runtime.tracing.trace import Trace
from runtime.tracing.trace_recorder import TraceRecorder


@dataclass(slots=True, kw_only=True)
class TraceContext:
    """
    Runtime tracing context.

    TraceContext provides the public API used by middleware and runtime
    components. It manages the current span stack while delegating span
    lifecycle operations to TraceRecorder.
    """

    recorder: TraceRecorder

    trace: Trace

    _span_stack: list[str] = field(default_factory=list)

    @property
    def current_span_id(self) -> str | None:
        """Return the current active span."""
        if not self._span_stack:
            return None

        return self._span_stack[-1]

    def _push_span(self, span_id: str) -> None:
        self._span_stack.append(span_id)

    def _pop_span(self) -> str | None:
        if not self._span_stack:
            return None

        return self._span_stack.pop()

    def start_span(self, name: str) -> Span:
        """
        Start a child span of the current active span.
        """

        span = self.recorder.start_span(
            trace=self.trace,
            name=name,
            parent_span_id=self.current_span_id,
            start_time=datetime.now(timezone.utc)
        )

    def end_span(self, status: SpanStatus = SpanStatus.SUCCESS) -> Span | None:
        """
        Finish the current active span.
        """

        if not self._span_stack:
            return None

        span_id = self._span_stack.pop()

        return self.recorder.end_span(
            trace=self.trace,
            span_id=span_id,
            status=status,
            end_time=datetime.now(timezone.utc)
        )