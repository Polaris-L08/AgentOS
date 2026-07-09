from runtime.events.event import Event
from tools import tool_event


def test_event_contains_trace_context():

    event = Event(
        type="tool.executed",
        source="tool",
        payload={
            "tool":"python"
        },
        trace_id="trace-1",
        span_id="span-2",
    )


    assert event.trace_id == "trace-1"

    assert event.span_id == "span-2"


def test_tool_event_builder_trace():

    event = tool_event.tool_executed(
        tool_name="python",
        trace_id="trace-1",
        span_id="span-1",
    )


    assert event.trace_id == "trace-1"

    assert event.span_id == "span-1"