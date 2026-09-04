import pytest

from runtime.execution.execution_handle import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


def create_execution_runtime() -> ExecutionRuntime:
    return ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )


def test_create_execution_returns_execution_handle():
    runtime = create_execution_runtime()

    handle = runtime.create_execution()

    assert isinstance(
        handle,
        ExecutionHandle,
    )


def test_execution_handle_contains_runtime_context():
    runtime = create_execution_runtime()

    handle = runtime.create_execution()

    assert handle.runtime_context is not None


def test_execution_handle_exposes_execution_id():
    runtime = create_execution_runtime()

    handle = runtime.create_execution()

    assert handle.execution_id
    assert (
        handle.execution_id
        == handle.runtime_context.runtime_id
    )


def test_execution_is_open_when_created():
    runtime = create_execution_runtime()

    handle = runtime.create_execution()

    assert handle.closed is False


def test_each_execution_has_unique_id():
    runtime = create_execution_runtime()

    handle_1 = runtime.create_execution()
    handle_2 = runtime.create_execution()

    assert (
        handle_1.execution_id
        != handle_2.execution_id
    )


def test_each_execution_has_independent_runtime_context():
    runtime = create_execution_runtime()

    handle_1 = runtime.create_execution()
    handle_2 = runtime.create_execution()

    assert (
        handle_1.runtime_context
        is not handle_2.runtime_context
    )


@pytest.mark.asyncio
async def test_close_marks_execution_as_closed():
    runtime = create_execution_runtime()

    handle = runtime.create_execution()

    await handle.close()

    assert handle.closed is True


@pytest.mark.asyncio
async def test_close_finalizes_trace():
    runtime = create_execution_runtime()

    handle = runtime.create_execution()

    assert (
        handle.runtime_context.trace.trace.end_time
        is None
    )

    await handle.close()

    assert (
        handle.runtime_context.trace.trace.end_time
        is not None
    )


@pytest.mark.asyncio
async def test_close_is_idempotent():
    runtime = create_execution_runtime()

    handle = runtime.create_execution()

    await handle.close()
    await handle.close()

    assert handle.closed is True


@pytest.mark.asyncio
async def test_async_context_manager_closes_execution():
    runtime = create_execution_runtime()

    async with runtime.create_execution() as handle:
        assert handle.closed is False

    assert handle.closed is True


@pytest.mark.asyncio
async def test_async_context_manager_closes_execution_on_exception():
    runtime = create_execution_runtime()

    handle = None

    with pytest.raises(
        RuntimeError,
        match="execution failed",
    ):
        async with runtime.create_execution() as execution:
            handle = execution

            raise RuntimeError("execution failed")

    assert handle is not None
    assert handle.closed is True


@pytest.mark.asyncio
async def test_runtime_context_remains_accessible_after_close():
    runtime = create_execution_runtime()

    handle = runtime.create_execution()

    runtime_context = handle.runtime_context

    await handle.close()

    assert handle.runtime_context is runtime_context


def test_low_level_create_context_still_works():
    runtime = create_execution_runtime()

    runtime_context = runtime.create_context()

    assert runtime_context is not None
    assert runtime_context.runtime_id


@pytest.mark.asyncio
async def test_low_level_close_still_works():
    runtime = create_execution_runtime()

    runtime_context = runtime.create_context()

    await runtime.close(runtime_context)

    assert (
        runtime_context.trace.trace.end_time
        is not None
    )