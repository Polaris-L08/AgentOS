import asyncio

import pytest

from models.task_request import TaskRequest
from runtime.application.application import AgentApplication
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.checkpoint import Checkpoint, MemoryCheckpointStore
from runtime.context.shared_context import SharedContext
from runtime.execution.execution import Execution
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.execution.execution_state import ExecutionStatus
from runtime.persistence import (
    InMemoryExecutionStore,
    InMemoryTaskStore,
)
from runtime.tracing.trace_recorder import TraceRecorder


def run_async(coro):
    return asyncio.run(coro)


class FakeAgent:
    pass


def create_application(
    *,
    task_store=None,
    execution_store=None,
    checkpoint_store=None,
):
    """
    Build a minimal Application instance for persistence integration
    tests.

    AgentRuntime is intentionally not exercised in these tests.
    """

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    application = AgentApplication(
        application_id="application-1",
        name="Persistence Integration Test",
        agent_runtime=FakeAgent(),
        execution_runtime=execution_runtime,
        task_store=task_store or InMemoryTaskStore(),
        execution_store=execution_store or InMemoryExecutionStore(),
        checkpoint_store=(
            checkpoint_store
            or MemoryCheckpointStore()
        ),
    )

    return application


def test_application_execute_persists_task_before_execution():
    async def scenario():
        task_store = InMemoryTaskStore()
        execution_store = InMemoryExecutionStore()

        application = create_application(
            task_store=task_store,
            execution_store=execution_store,
        )

        task = TaskRequest(
            task_id="task-1",
            user_input="analyze NVIDIA",
        )

        await task_store.save(task)

        loaded = await task_store.load(task.task_id)

        assert loaded == task

    run_async(scenario())


def test_checkpoint_persistence_binds_checkpoint_to_execution():
    async def scenario():
        task_store = InMemoryTaskStore()
        execution_store = InMemoryExecutionStore()
        checkpoint_store = MemoryCheckpointStore()

        application = create_application(
            task_store=task_store,
            execution_store=execution_store,
            checkpoint_store=checkpoint_store,
        )

        execution = Execution(
            execution_id="execution-1",
            task_id="task-1",
        )

        handle = application.execution_runtime.create_execution(
            execution
        )

        try:
            checkpoint = Checkpoint(
                checkpoint_id="checkpoint-1",
                runtime_id=handle.runtime_id,
                shared_context=SharedContext(),
                agents={},
                task_id="task-1",
            )

            await application.initialize()
            await application.start()

            await application.persist_checkpoint(
                execution_handle=handle,
                checkpoint=checkpoint,
            )

            stored_checkpoint = await checkpoint_store.load(
                checkpoint.checkpoint_id
            )

            assert stored_checkpoint is not None
            assert (
                stored_checkpoint.checkpoint_id
                == checkpoint.checkpoint_id
            )
            assert (
                stored_checkpoint.runtime_id
                == handle.runtime_id
            )
            assert stored_checkpoint.task_id == "task-1"

            stored_execution = await execution_store.load(
                execution.execution_id
            )

            assert stored_execution is not None
            assert (
                stored_execution.current_checkpoint_id
                == checkpoint.checkpoint_id
            )

        finally:
            await handle.close()

            if application.is_running:
                await application.stop()

    run_async(scenario())


def test_checkpoint_is_persisted_before_execution_references_it():
    async def scenario():
        execution_store = InMemoryExecutionStore()
        checkpoint_store = MemoryCheckpointStore()

        application = create_application(
            execution_store=execution_store,
            checkpoint_store=checkpoint_store,
        )

        execution = Execution(
            execution_id="execution-order",
            task_id="task-order",
        )

        handle = application.execution_runtime.create_execution(
            execution
        )

        try:
            await application.initialize()
            await application.start()

            checkpoint = Checkpoint(
                checkpoint_id="checkpoint-order",
                runtime_id=handle.runtime_id,
                shared_context=SharedContext(),
                agents={},
                task_id="task-order",
            )

            await application.persist_checkpoint(
                execution_handle=handle,
                checkpoint=checkpoint,
            )

            stored_checkpoint = await checkpoint_store.load(
                "checkpoint-order"
            )

            stored_execution = await execution_store.load(
                "execution-order"
            )

            assert stored_checkpoint is not None
            assert stored_execution is not None

            assert (
                stored_execution.current_checkpoint_id
                == stored_checkpoint.checkpoint_id
            )

        finally:
            await handle.close()

            if application.is_running:
                await application.stop()

    run_async(scenario())


def test_checkpoint_task_id_mismatch_is_rejected():
    async def scenario():
        application = create_application()

        execution = Execution(
            execution_id="execution-mismatch",
            task_id="task-execution",
        )

        handle = application.execution_runtime.create_execution(
            execution
        )

        try:
            await application.initialize()
            await application.start()

            checkpoint = Checkpoint(
                checkpoint_id="checkpoint-mismatch",
                runtime_id=handle.runtime_id,
                shared_context=SharedContext(),
                agents={},
                task_id="task-checkpoint",
            )

            with pytest.raises(
                ApplicationLifecycleError,
                match=(
                    "Checkpoint task_id does not match "
                    "Execution task_id"
                ),
            ):
                await application.persist_checkpoint(
                    execution_handle=handle,
                    checkpoint=checkpoint,
                )

        finally:
            await handle.close()

            if application.is_running:
                await application.stop()

    run_async(scenario())


def test_checkpoint_runtime_id_mismatch_is_rejected():
    async def scenario():
        application = create_application()

        execution = Execution(
            execution_id="execution-runtime-mismatch",
            task_id="task-runtime-mismatch",
        )

        handle = application.execution_runtime.create_execution(
            execution
        )

        try:
            await application.initialize()
            await application.start()

            checkpoint = Checkpoint(
                checkpoint_id="checkpoint-runtime-mismatch",
                runtime_id="different-runtime-id",
                shared_context=SharedContext(),
                agents={},
                task_id="task-runtime-mismatch",
            )

            with pytest.raises(
                ApplicationLifecycleError,
                match=(
                    "Checkpoint runtime_id does not match "
                    "Execution runtime_id"
                ),
            ):
                await application.persist_checkpoint(
                    execution_handle=handle,
                    checkpoint=checkpoint,
                )

        finally:
            await handle.close()

            if application.is_running:
                await application.stop()

    run_async(scenario())


def test_checkpoint_persistence_does_not_change_execution_status():
    async def scenario():
        execution_store = InMemoryExecutionStore()
        checkpoint_store = MemoryCheckpointStore()

        application = create_application(
            execution_store=execution_store,
            checkpoint_store=checkpoint_store,
        )

        execution = Execution(
            execution_id="execution-status",
            task_id="task-status",
            status=ExecutionStatus.RUNNING,
        )

        handle = application.execution_runtime.create_execution(
            execution
        )

        try:
            await application.initialize()
            await application.start()

            checkpoint = Checkpoint(
                checkpoint_id="checkpoint-status",
                runtime_id=handle.runtime_id,
                shared_context=SharedContext(),
                agents={},
                task_id="task-status",
            )

            await application.persist_checkpoint(
                execution_handle=handle,
                checkpoint=checkpoint,
            )

            assert (
                execution.status
                == ExecutionStatus.RUNNING
            )

            stored_execution = await execution_store.load(
                execution.execution_id
            )

            assert stored_execution is not None
            assert (
                stored_execution.status
                == ExecutionStatus.RUNNING
            )

        finally:
            await handle.close()

            if application.is_running:
                await application.stop()

    run_async(scenario())