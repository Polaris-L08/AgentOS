from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any

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

    @property
    def current_span(self) -> Span | None:
        """
        Return current active span.
        """
        span_id = self.current_span_id

        if span_id is None:
            return None

        return self.trace.get_span(span_id=span_id)

    def _push_span(self, span_id: str) -> None:
        self._span_stack.append(span_id)

    def _pop_span(self) -> str | None:
        if not self._span_stack:
            return None

        return self._span_stack.pop()

    def start_span(self, name: str, metadata: dict[str, Any] | None = None) -> Span:
        """
        Start a child span of the current active span.
        """
        now = datetime.now(timezone.utc)

        span = self.recorder.start_span(
            trace=self.trace,
            name=name,
            parent_span_id=self.current_span_id,
            start_time=now,
            metadata=metadata or {}
        )

        self._push_span(span_id=span.span_id)

        return span

    def end_span(self, status: SpanStatus = SpanStatus.SUCCESS) -> Span | None:
        """
        Finish the current active span.
        """

        if not self._span_stack:
            return None

        span_id = self._pop_span()

        if span_id is None:
            return None

        now = datetime.now(timezone.utc)

        return self.recorder.end_span(
            trace=self.trace,
            span_id=span_id,
            status=status,
            end_time=now
        )

    @contextmanager
    def span(self, name: str) -> Iterator[Span]:
        """
        Create a tracing scope.

        Example:
            with trace_context.span("tool.execute"):
                ...
        """
        span = self.start_span(name)

        try:
            yield span
        except Exception:
            self.end_span(SpanStatus.ERROR)
            raise
        else:
            self.end_span(SpanStatus.SUCCESS)