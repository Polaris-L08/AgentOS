from datetime import datetime, timezone

from runtime.tracing.trace import Trace
from runtime.tracing.span import Span


def test_add_and_get_span():
    now = datetime.now(timezone.utc)

    trace = Trace(
        trace_id="trace-1",
        root_span_id="span-root",
        start_time=now,
    )

    span = Span(
        span_id="span-1",
        trace_id="trace-1",
        name="tool.execute",
        start_time=now,
    )

    trace.add_span(span)

    assert trace.get_span("span-1") == span
    assert len(trace.all_spans()) == 1


def test_trace_duration():
    now = datetime.now(timezone.utc)

    trace = Trace(
        trace_id="trace-1",
        root_span_id="span-root",
        start_time=now,
        end_time=now,
    )

    assert trace.duration_ms == 0.0