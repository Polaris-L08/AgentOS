from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from runtime.tracing.span import Span
from runtime.tracing.trace import Trace
from runtime.tracing.trace_recorder import TraceRecorder


@dataclass(slots=True, kw_only=True)
class TraceContext:
    """
    High-level API for tracing system.

    This is the ONLY interface exposed to runtime (Agent / Tool / Middleware).

    It hides Trace and Recorder complexity.
    """

    recorder: TraceRecorder

    trace: Trace

    current_span_id: Optional[str] = None

    def start_span(self, name: str, parent_span_id: Optional[str] = None) -> Span:
        """
        Start a new span and register it into trace.
        """
        now = datetime.now(timezone.utc)

        span = self.recorder.start_span(trace=self.trace, name=name, start_time=now, parent_span_id=parent_span_id)

        self.current_span_id = span.span_id

        return span

    def end_span(self, status: str = "success") -> None:
        """
        End current span.
        """

        now = datetime.now(timezone.utc)

        self.recorder.end_span(
            trace=self.trace,
            span_id=self.current_span_id,
            end_time=now,
            status=status
        )