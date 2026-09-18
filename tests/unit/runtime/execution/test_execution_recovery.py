from __future__ import annotations

from datetime import datetime, timezone

import pytest

from runtime.checkpoint.checkpoint import Checkpoint
from runtime.context.shared_context import SharedContext
from runtime.execution.execution import Execution
from runtime.execution.execution_handle import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace import Trace
from runtime.tracing.trace_context import TraceContext
from runtime.tracing.trace_recorder import TraceRecorder


def create_runtime() -> ExecutionRuntime:
    return ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )


def create_execution(
    execution_id: str = "execution-001",
) -> Execution:
    return Execution(
        execution_id=execution_id,
        task_id="task-001",
    )


def create_checkpoint(
    runtime_id: str = "runtime-001",
) -> Checkpoint:
    return Checkpoint(
        runtime_id=runtime_id,
        task_id="task-001",
        shared_context=SharedContext(),
        agents={},
    )


def create_trace_context(
    trace_id: str = "trace-test",
) -> TraceContext:
    trace = Trace(
        trace_id=trace_id,
        start_time=datetime.now(timezone.utc),
    )

    return TraceContext(
        recorder=TraceRecorder(),
        trace=trace,
    )


def test_resume_execution_returns_execution_handle():
    runtime = create_runtime()
    execution = create_execution()
    checkpoint = create_checkpoint()

    handle = runtime.resume_execution(
        execution=execution,
        checkpoint=checkpoint,
    )

    assert isinstance(handle, ExecutionHandle)


def test_resume_execution_preserves_logical_execution_id():
    runtime = create_runtime()
    execution = create_execution(
        execution_id="execution-123",
    )
    checkpoint = create_checkpoint(
        runtime_id="runtime-123",
    )

    handle = runtime.resume_execution(
        execution=execution,
        checkpoint=checkpoint,
    )

    assert handle.execution_id == "execution-123"
    assert handle.execution_id == execution.execution_id


def test_resume_execution_preserves_checkpoint_runtime_id():
    runtime = create_runtime()
    execution = create_execution(
        execution_id="execution-123",
    )
    checkpoint = create_checkpoint(
        runtime_id="runtime-123",
    )

    handle = runtime.resume_execution(
        execution=execution,
        checkpoint=checkpoint,
    )

    assert handle.runtime_id == "runtime-123"
    assert handle.runtime_context.runtime_id == "runtime-123"


def test_execution_id_and_runtime_id_are_distinct():
    runtime = create_runtime()
    execution = create_execution(
        execution_id="execution-123",
    )
    checkpoint = create_checkpoint(
        runtime_id="runtime-123",
    )

    handle = runtime.resume_execution(
        execution=execution,
        checkpoint=checkpoint,
    )

    assert handle.execution_id != handle.runtime_id


def test_resume_execution_preserves_execution_object():
    runtime = create_runtime()
    execution = create_execution()
    checkpoint = create_checkpoint()

    handle = runtime.resume_execution(
        execution=execution,
        checkpoint=checkpoint,
    )

    assert handle.execution is execution


def test_resume_execution_creates_new_trace_id():
    runtime = create_runtime()
    execution = create_execution()
    checkpoint = create_checkpoint(
        runtime_id="runtime-123",
    )

    handle = runtime.resume_execution(
        execution=execution,
        checkpoint=checkpoint,
    )

    assert (
        handle.runtime_context.trace.trace.trace_id
        != checkpoint.runtime_id
    )


def test_resume_execution_restores_shared_context():
    runtime = create_runtime()
    execution = create_execution()

    shared_context = SharedContext()

    checkpoint = Checkpoint(
        runtime_id="runtime-123",
        task_id="task-001",
        shared_context=shared_context,
        agents={},
    )

    handle = runtime.resume_execution(
        execution=execution,
        checkpoint=checkpoint,
    )

    assert (
        handle.runtime_context.shared_context
        is shared_context
    )