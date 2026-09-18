import pytest

from runtime.execution.execution import Execution
from runtime.execution.execution_handle import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


def create_execution_runtime() -> ExecutionRuntime:
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


def test_create_execution_returns_execution_handle():
    runtime = create_execution_runtime()
    execution = create_execution()

    handle = runtime.create_execution(
        execution=execution,
    )

    assert isinstance(handle, ExecutionHandle)


def test_execution_handle_contains_execution():
    runtime = create_execution_runtime()
    execution = create_execution()

    handle = runtime.create_execution(
        execution=execution,
    )

    assert handle.execution is execution


def test_execution_handle_contains_runtime_context():
    runtime = create_execution_runtime()
    execution = create_execution()

    handle = runtime.create_execution(
        execution=execution,
    )

    assert handle.runtime_context is not None


def test_execution_id_comes_from_execution():
    runtime = create_execution_runtime()
    execution = create_execution(
        execution_id="execution-123",
    )

    handle = runtime.create_execution(
        execution=execution,
    )

    assert handle.execution_id == "execution-123"


def test_execution_id_is_not_runtime_id():
    runtime = create_execution_runtime()
    execution = create_execution(
        execution_id="execution-123",
    )

    handle = runtime.create_execution(
        execution=execution,
    )

    assert handle.execution_id == execution.execution_id
    assert handle.runtime_id == handle.runtime_context.runtime_id
    assert handle.execution_id != handle.runtime_id


def test_execution_and_runtime_context_are_separate_objects():
    runtime = create_execution_runtime()
    execution = create_execution()

    handle = runtime.create_execution(
        execution=execution,
    )

    assert handle.execution is execution
    assert handle.runtime_context is not execution


def test_execution_is_open_when_created():
    runtime = create_execution_runtime()
    execution = create_execution()

    handle = runtime.create_execution(
        execution=execution,
    )

    assert handle.closed is False


def test_each_execution_has_unique_runtime_context():
    runtime = create_execution_runtime()

    execution_1 = create_execution("execution-001")
    execution_2 = create_execution("execution-002")

    handle_1 = runtime.create_execution(
        execution=execution_1,
    )
    handle_2 = runtime.create_execution(
        execution=execution_2,
    )

    assert handle_1.runtime_context is not handle_2.runtime_context
    assert handle_1.execution is not handle_2.execution


@pytest.mark.asyncio
async def test_close_marks_execution_as_closed():
    runtime = create_execution_runtime()
    execution = create_execution()

    handle = runtime.create_execution(
        execution=execution,
    )

    await handle.close()

    assert handle.closed is True


@pytest.mark.asyncio
async def test_close_finalizes_trace():
    runtime = create_execution_runtime()
    execution = create_execution()

    handle = runtime.create_execution(
        execution=execution,
    )

    assert handle.runtime_context.trace.trace.end_time is None

    await handle.close()

    assert handle.runtime_context.trace.trace.end_time is not None


@pytest.mark.asyncio
async def test_close_is_idempotent():
    runtime = create_execution_runtime()
    execution = create_execution()

    handle = runtime.create_execution(
        execution=execution,
    )

    await handle.close()
    await handle.close()

    assert handle.closed is True


@pytest.mark.asyncio
async def test_async_context_manager_closes_execution():
    runtime = create_execution_runtime()
    execution = create_execution()

    async with runtime.create_execution(
        execution=execution,
    ) as handle:
        assert handle.closed is False

    assert handle.closed is True


@pytest.mark.asyncio
async def test_async_context_manager_closes_execution_on_exception():
    runtime = create_execution_runtime()
    execution = create_execution()

    handle = None

    with pytest.raises(
        RuntimeError,
        match="execution failed",
    ):
        async with runtime.create_execution(
            execution=execution,
        ) as current_handle:
            handle = current_handle
            raise RuntimeError("execution failed")

    assert handle is not None
    assert handle.closed is True


@pytest.mark.asyncio
async def test_runtime_context_remains_accessible_after_close():
    runtime = create_execution_runtime()
    execution = create_execution()

    handle = runtime.create_execution(
        execution=execution,
    )

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

    assert runtime_context.trace.trace.end_time is not None