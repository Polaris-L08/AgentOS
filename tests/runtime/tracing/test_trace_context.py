from datetime import datetime, timezone

from runtime.tracing.trace import Trace
from runtime.tracing.trace_context import TraceContext
from runtime.tracing.trace_recorder import TraceRecorder


def test_trace_context_span_lifecycle():
    recorder = TraceRecorder()

    trace = Trace(
        trace_id="trace-1",
        root_span_id="root",
        start_time=datetime.now(timezone.utc),
    )

    ctx = TraceContext(
        recorder=recorder,
        trace=trace,
    )

    span = ctx.start_span("tool.execute")

    assert span.span_id in trace.spans
    assert ctx.current_span_id == span.span_id

    ctx.end_span("success")

    assert trace.get_span(span.span_id).status.value == "success"