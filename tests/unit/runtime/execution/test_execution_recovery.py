from __future__ import annotations

from datetime import datetime, timezone

import pytest

from runtime.checkpoint.checkpoint import Checkpoint
from runtime.context.shared_context import SharedContext
from runtime.execution.execution_handle import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace import Trace
from runtime.tracing.trace_context import TraceContext
from runtime.tracing.trace_recorder import TraceRecorder


def create_runtime() -> ExecutionRuntime:
    return ExecutionRuntime(
        trace_recorder=TraceRecorder()
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
    checkpoint = create_checkpoint()

    handle = runtime.resume_execution(checkpoint)

    assert isinstance(handle, ExecutionHandle)


def test_resume_execution_preserves_runtime_id():
    runtime = create_runtime()
    checkpoint = create_checkpoint(
        runtime_id="runtime-123",
    )

    handle = runtime.resume_execution(checkpoint)

    assert handle.execution_id == "runtime-123"
    assert handle.runtime_context.runtime_id == "runtime-123"


def test_resume_execution_creates_new_trace_id():
    runtime = create_runtime()
    checkpoint = create_checkpoint(
        runtime_id="runtime-123",
    )

    handle = runtime.resume_execution(checkpoint)

    assert (
        handle.runtime_context.trace.trace.trace_id
        != checkpoint.runtime_id
    )


def test_resume_execution_restores_shared_context():
    runtime = create_runtime()

    shared_context = SharedContext()

    checkpoint = Checkpoint(
        runtime_id="runtime-123",
        task_id="task-123",
        shared_context=shared_context,
        agents={},
    )

    handle = runtime.resume_execution(checkpoint)

    assert (
        handle.runtime_context.shared_context
        is shared_context
    )


def test_resume_execution_creates_recovery_span():
    runtime = create_runtime()
    checkpoint = create_checkpoint()

    handle = runtime.resume_execution(checkpoint)

    trace_context = handle.runtime_context.trace

    assert trace_context.current_span is not None
    assert trace_context.current_span.name == "agent.resume"
    assert trace_context.current_span.metadata["type"] == "recovery"
    assert (
        trace_context.current_span.metadata["runtime_id"]
        == checkpoint.runtime_id
    )


def test_resume_execution_trace_is_independent_from_checkpoint():
    runtime = create_runtime()
    checkpoint = create_checkpoint(
        runtime_id="runtime-123",
    )

    handle = runtime.resume_execution(checkpoint)

    assert (
        handle.runtime_context.trace.trace.trace_id
        != "runtime-123"
    )


@pytest.mark.asyncio
async def test_recovered_execution_can_be_closed():
    runtime = create_runtime()
    checkpoint = create_checkpoint()

    handle = runtime.resume_execution(checkpoint)

    trace_context = handle.runtime_context.trace
    trace = trace_context.trace

    assert handle.closed is False
    assert trace_context.current_span is not None
    assert trace.end_time is None

    await handle.close()

    assert handle.closed is True
    assert trace_context.current_span is None
    assert trace.end_time is not None


def test_new_execution_and_recovered_execution_have_same_handle_type():
    runtime = create_runtime()
    checkpoint = create_checkpoint()

    new_handle = runtime.create_execution()
    recovered_handle = runtime.resume_execution(checkpoint)

    assert isinstance(new_handle, ExecutionHandle)
    assert isinstance(recovered_handle, ExecutionHandle)


def test_new_execution_and_recovered_execution_have_different_runtime_ids():
    runtime = create_runtime()
    checkpoint = create_checkpoint(
        runtime_id="recovered-runtime",
    )

    new_handle = runtime.create_execution()
    recovered_handle = runtime.resume_execution(checkpoint)

    assert (
        new_handle.execution_id
        != recovered_handle.execution_id
    )


def test_recovered_execution_preserves_checkpoint_runtime_identity():
    runtime = create_runtime()

    checkpoint = create_checkpoint(
        runtime_id="execution-42",
    )

    handle = runtime.resume_execution(checkpoint)

    assert handle.execution_id == "execution-42"


@pytest.mark.asyncio
async def test_recovered_execution_close_is_idempotent():
    runtime = create_runtime()
    checkpoint = create_checkpoint()

    handle = runtime.resume_execution(checkpoint)

    await handle.close()
    await handle.close()

    assert handle.closed is True


def test_create_context_from_checkpoint_preserves_runtime_id():
    runtime = create_runtime()

    checkpoint = create_checkpoint(
        runtime_id="execution-99",
    )

    context = runtime.create_context_from_checkpoint(
        checkpoint
    )

    assert context.runtime_id == "execution-99"


def test_create_context_from_checkpoint_creates_new_trace():
    runtime = create_runtime()

    checkpoint = create_checkpoint(
        runtime_id="execution-99",
    )

    context = runtime.create_context_from_checkpoint(
        checkpoint
    )

    assert context.trace.trace.trace_id != "execution-99"


def test_create_context_from_checkpoint_preserves_shared_context():
    runtime = create_runtime()

    shared_context = SharedContext()

    checkpoint = Checkpoint(
        runtime_id="execution-99",
        task_id="task-99",
        shared_context=shared_context,
        agents={},
    )

    context = runtime.create_context_from_checkpoint(
        checkpoint
    )

    assert context.shared_context is shared_context


def test_normal_execution_still_creates_unique_runtime_ids():
    runtime = create_runtime()

    handle1 = runtime.create_execution()
    handle2 = runtime.create_execution()

    assert handle1.execution_id != handle2.execution_id


@pytest.mark.asyncio
async def test_recovered_execution_trace_is_finalized_on_close():
    runtime = create_runtime()

    checkpoint = create_checkpoint()

    handle = runtime.resume_execution(checkpoint)

    trace = handle.runtime_context.trace.trace

    assert trace.end_time is None

    await handle.close()

    assert trace.end_time is not None