from __future__ import annotations

import pytest

from runtime.events.event_bus import EventBus
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


@pytest.fixture
def event_bus():

    return EventBus()



@pytest.fixture
def runtime_context():
    trace_recorder = TraceRecorder()
    execution_runtime = ExecutionRuntime(trace_recorder)
    runtime_context = execution_runtime.create_context()
    return runtime_context