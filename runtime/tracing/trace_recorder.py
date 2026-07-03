from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from runtime.tracing.span import Span, SpanStatus
from runtime.tracing.trace import Trace


@dataclass(slots=True, kw_only=True)
class TraceRecorder:
    """
    Domain service responsible for span lifecycle management.
    """

    def start_span(self,
                   trace: Trace,
                   name: str,
                   start_time: datetime,
                   parent_span_id: str | None
                   ) -> Span:
        """
        Create and register a new span.
        """

        span_id = f"span-{trace.span_count + 1}"

        span = Span(
            span_id=span_id,
            trace_id=trace.trace_id,
            name=name,
            start_time=start_time,
            parent_span_id=parent_span_id
        )

        trace.add_span(span)

        return span


    def end_span(self,
                 trace: Trace,
                 span_id: str | None,
                 end_time: datetime,
                 status: SpanStatus
                 ) -> Span | None:
        """
        Finalize span.
        """

        if span_id is None:
            return None

        span = trace.get_span(span_id)
        if span is None:
            return None

        span.end_time = end_time
        span.status = status

        return span