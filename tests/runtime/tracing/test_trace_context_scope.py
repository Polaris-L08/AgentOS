from datetime import datetime, timezone

from runtime.tracing.span import SpanStatus
import pytest

from runtime.tracing.trace import Trace
from runtime.tracing.trace_context import TraceContext
from runtime.tracing.trace_recorder import TraceRecorder

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

# 正常结束
def test_span_scope_success():
    with ctx.span("tool.execute"):
        pass

    span = trace.all_spans()[0]

    assert span.status == SpanStatus.SUCCESS


# 异常结束
def test_span_scope_error():

    with pytest.raises(RuntimeError):

        with ctx.span("tool.execute"):
            raise RuntimeError()

    span = trace.all_spans()[0]

    assert span.status == SpanStatus.ERROR


