from datetime import datetime, timedelta, timezone

from runtime.tracing.span import Span
from runtime.tracing.span import SpanStatus
from runtime.tracing.trace import Trace
from runtime.tracing.trace_formatter import TraceFormatter


def test_trace_formatter():

    now = datetime.now(timezone.utc)

    trace = Trace(
        trace_id="trace-1",
        start_time=now,
        end_time=now + timedelta(seconds=5),
    )

    root = Span(
        span_id="1",
        trace_id="trace-1",
        name="agent.run",
        start_time=now,
        end_time=now + timedelta(seconds=5),
        status=SpanStatus.SUCCESS,
    )

    planner = Span(
        span_id="2",
        trace_id="trace-1",
        parent_span_id="1",
        name="planner.plan",
        start_time=now,
        end_time=now + timedelta(milliseconds=200),
        status=SpanStatus.SUCCESS,
    )

    tool = Span(
        span_id="3",
        trace_id="trace-1",
        parent_span_id="1",
        name="tool.execute",
        start_time=now,
        end_time=now + timedelta(seconds=3),
        status=SpanStatus.SUCCESS,
    )

    trace.add_span(root)
    trace.add_span(planner)
    trace.add_span(tool)

    formatter = TraceFormatter()

    report = formatter.format(trace)

    print(report)

    assert "Trace Report" in report
    assert "agent.run" in report
    assert "planner.plan" in report
    assert "tool.execute" in report
    assert "SUCCESS" in report