import pytest

from runtime.events.event_bus import EventBus
from tools import ToolExecutor
from tools.registry import ToolRegistry
from tools import ToolRequest
from runtime.events.event import Event
from tests.event.recording_subscriber import RecordingSubscriber


def test_event():
    event = Event(
        type="tool.exected",
        source="tool_executor",
        trace_id="trace_001"
    )

    assert event.type == "tool.executed"
    assert event.source == "tool_executor"
    assert event.trace_id == "trace-001"

    assert event.id

    event1 = Event(...)
    event2 = Event(...)

    assert event1.id != event2.id

    assert event.timestamp.tzinfo is not None

@pytest.mark.asyncio
def test_tool_executed_event():
    bus = EventBus()
    recorder = RecordingSubscriber()

    bus.subscribe("tool.executed", recorder)

    event = Event(
        type="tool.executed",
        source="tool_executor",
        payload={"tool_name": "read_file"}
    )

    bus.emit(event)

    assert len(recorder.events) == 1
    assert recorder.events[0].type == "tool.executed"
    assert recorder.events[0].payload["tool_name"] == "read_file"

@pytest.mark.asyncio
def test_tool_failed_event():
    bus = EventBus()
    recorder = RecordingSubscriber()

    bus.subscribe("tool.failed", recorder)

    event = Event(
        type="tool.failed",
        source="tool_executor",
        payload={
            "tool_name": "read_file",
            "error": "File not found"
        }
    )

    bus.emit(event)

    assert len(recorder.events) == 1
    assert recorder.events[0].type == "tool.failed"
    assert recorder.events[0].payload["error"] == "File not found"

@pytest.mark.asyncio
def test_tool_executor_event_flow():
    bus = EventBus()
    recorder = RecordingSubscriber()

    bus.subscribe("tool.executed", recorder)
    bus.subscribe("tool.failed", recorder)

    executor = ToolExecutor(
        publisher=bus,
        registry=ToolRegistry()
    )

    request = ToolRequest(tool_name="echo", args={"msg": "hi"})

    result = executor.execute(request)

    # ToolResult 正常返回
    assert result is not None

    # Event 被触发
    assert len(recorder.events) == 1
    assert recorder.events[0].type == "tool.executed"