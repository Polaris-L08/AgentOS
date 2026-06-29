from datetime import datetime, timedelta, timezone

from runtime.tracing.span import Span, SpanStatus


def test_create_span():
    now = datetime.now(timezone.utc)

    span = Span(
        span_id="span-1",
        trace_id="trace-1",
        name="tool.execute",
        start_time=now
    )

    assert span.span_id == "span-1"
    assert span.trace_id == "trace-1"
    assert span.name == "tool.execute"
    assert span.status == SpanStatus.RUNNING
    assert span.end_time is None
    assert span.duration_ms is None


def test_span_duration():
    start = datetime.now(timezone.utc)
    end = start + timedelta(milliseconds=125)

    span = Span(
        span_id="span-1",
        trace_id="trace-1",
        name="tool.execute",
        start_time=start,
        end_time=end,
        status=SpanStatus.SUCCESS
    )

    assert span.duration_ms == 125.0