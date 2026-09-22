import asyncio
from unittest.mock import Mock

import pytest

from runtime.application.application_executor import (
    ApplicationExecutor,
)
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.checkpoint import Checkpoint
from runtime.checkpoint.memory_checkpoint_store import (
    MemoryCheckpointStore,
)
from runtime.context.shared_context import SharedContext
from runtime.execution.execution import Execution
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.execution.execution_state import ExecutionStatus
from runtime.orchestration import Orchestrator
from runtime.persistence.in_memory_execution_store import (
    InMemoryExecutionStore,
)
from runtime.persistence.in_memory_task_store import (
    InMemoryTaskStore,
)
from runtime.tracing.trace_recorder import TraceRecorder


def run_async(coro):
    return asyncio.run(coro)


def create_executor():
    execution_store = InMemoryExecutionStore()
    task_store = InMemoryTaskStore()
    checkpoint_store = MemoryCheckpointStore()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    orchestrator = Mock(spec=Orchestrator)

    executor = ApplicationExecutor(
        execution_runtime=execution_runtime,
        orchestrator=orchestrator,
        execution_store=execution_store,
        task_store=task_store,
        checkpoint_store=checkpoint_store,
    )

    return (
        executor,
        execution_store,
        task_store,
        checkpoint_store,
        orchestrator,
    )


def create_paused_execution(
    *,
    execution_id: str = "execution-1",
    task_id: str | None = "task-1",
    checkpoint_id: str = "checkpoint-1",
) -> Execution:
    return Execution(
        execution_id=execution_id,
        task_id=task_id,
        current_checkpoint_id=checkpoint_id,
        status=ExecutionStatus.PAUSED,
    )


def create_checkpoint(
    *,
    checkpoint_id: str = "checkpoint-1",
    runtime_id: str = "runtime-1",
    task_id: str | None = "task-1",
) -> Checkpoint:
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id=runtime_id,
        shared_context=SharedContext(),
        agents={},
        task_id=task_id,
    )


def test_executor_does_not_depend_on_application():
    executor, _, _, _, _ = create_executor()

    assert not hasattr(executor, "_application")


def test_executor_stores_explicit_dependencies():
    (
        executor,
        execution_store,
        task_store,
        checkpoint_store,
        orchestrator,
    ) = create_executor()

    assert executor._execution_store is execution_store
    assert executor._task_store is task_store
    assert executor._checkpoint_store is checkpoint_store
    assert executor._orchestrator is orchestrator


def test_executor_does_not_own_agent_runtime():
    executor, _, _, _, _ = create_executor()

    assert not hasattr(executor, "_agent_runtime")
    assert not hasattr(executor, "_agent_registry")


def test_recover_persisted_execution_successfully():
    async def scenario():
        (
            executor,
            execution_store,
            _,
            checkpoint_store,
            _,
        ) = create_executor()

        execution = create_paused_execution(
            execution_id="execution-1",
            task_id="task-1",
            checkpoint_id="checkpoint-1",
        )

        checkpoint = create_checkpoint(
            checkpoint_id="checkpoint-1",
            runtime_id="runtime-1",
            task_id="task-1",
        )

        await execution_store.save(
            execution.snapshot()
        )

        await checkpoint_store.save(
            checkpoint.checkpoint_id,
            checkpoint,
        )

        handle = await executor.recover_persisted_execution(
            execution_id=execution.execution_id
        )

        try:
            assert handle.execution_id == execution.execution_id
            assert handle.runtime_id == checkpoint.runtime_id
            assert (
                handle.execution.execution_id
                == execution.execution_id
            )
            assert (
                handle.execution.task_id
                == execution.task_id
            )
            assert (
                handle.execution.current_checkpoint_id
                == checkpoint.checkpoint_id
            )
            assert (
                handle.execution.status
                == ExecutionStatus.PAUSED
            )
            assert (
                handle.runtime_context.runtime_id
                == checkpoint.runtime_id
            )
            assert (
                handle.runtime_context.shared_context.data
                == checkpoint.shared_context.data
            )
        finally:
            await handle.close()

    run_async(scenario())


def test_recover_persisted_execution_preserves_execution_identity():
    async def scenario():
        (
            executor,
            execution_store,
            _,
            checkpoint_store,
            _,
        ) = create_executor()

        execution = create_paused_execution(
            execution_id="logical-execution-123",
            task_id="task-123",
            checkpoint_id="checkpoint-123",
        )

        checkpoint = create_checkpoint(
            checkpoint_id="checkpoint-123",
            runtime_id="runtime-before-crash",
            task_id="task-123",
        )

        await execution_store.save(
            execution.snapshot()
        )

        await checkpoint_store.save(
            checkpoint.checkpoint_id,
            checkpoint,
        )

        handle = await executor.recover_persisted_execution(
            execution_id=execution.execution_id
        )

        try:
            assert (
                handle.execution_id
                == "logical-execution-123"
            )

            assert (
                handle.runtime_id
                == "runtime-before-crash"
            )

            assert (
                handle.execution_id
                != handle.runtime_id
            )
        finally:
            await handle.close()

    run_async(scenario())


def test_recover_persisted_execution_fails_when_execution_does_not_exist():
    async def scenario():
        executor, _, _, _, _ = create_executor()

        with pytest.raises(
            ApplicationLifecycleError,
            match="Execution not found: execution-missing",
        ):
            await executor.recover_persisted_execution(
                execution_id="execution-missing"
            )

    run_async(scenario())


def test_recover_persisted_execution_fails_when_execution_has_no_checkpoint():
    async def scenario():
        (
            executor,
            execution_store,
            _,
            _,
            _,
        ) = create_executor()

        execution = Execution(
            execution_id="execution-no-checkpoint",
            task_id="task-1",
            status=ExecutionStatus.PAUSED,
        )

        await execution_store.save(
            execution.snapshot()
        )

        with pytest.raises(
            ApplicationLifecycleError,
            match=(
                "Execution does not have a recovery checkpoint: "
                "execution-no-checkpoint"
            ),
        ):
            await executor.recover_persisted_execution(
                execution_id=execution.execution_id
            )

    run_async(scenario())


def test_recover_persisted_execution_fails_when_checkpoint_does_not_exist():
    async def scenario():
        (
            executor,
            execution_store,
            _,
            _,
            _,
        ) = create_executor()

        execution = create_paused_execution(
            execution_id="execution-checkpoint-missing",
            task_id="task-1",
            checkpoint_id="checkpoint-missing",
        )

        await execution_store.save(
            execution.snapshot()
        )

        with pytest.raises(
            ApplicationLifecycleError,
            match=(
                "Checkpoint not found for Execution: "
                "execution-checkpoint-missing: "
                "checkpoint-missing"
            ),
        ):
            await executor.recover_persisted_execution(
                execution_id=execution.execution_id
            )

    run_async(scenario())


def test_recover_persisted_execution_fails_when_task_id_does_not_match():
    async def scenario():
        (
            executor,
            execution_store,
            _,
            checkpoint_store,
            _,
        ) = create_executor()

        execution = create_paused_execution(
            execution_id="execution-task-mismatch",
            task_id="task-execution",
            checkpoint_id="checkpoint-task-mismatch",
        )

        checkpoint = create_checkpoint(
            checkpoint_id="checkpoint-task-mismatch",
            runtime_id="runtime-task-mismatch",
            task_id="task-checkpoint",
        )

        await execution_store.save(
            execution.snapshot()
        )

        await checkpoint_store.save(
            checkpoint.checkpoint_id,
            checkpoint,
        )

        with pytest.raises(
            ApplicationLifecycleError,
            match=(
                "Checkpoint task_id does not match "
                "Execution task_id: "
                "execution=task-execution, "
                "checkpoint=task-checkpoint"
            ),
        ):
            await executor.recover_persisted_execution(
                execution_id=execution.execution_id
            )

    run_async(scenario())


def test_recover_persisted_execution_restores_shared_context():
    async def scenario():
        (
            executor,
            execution_store,
            _,
            checkpoint_store,
            _,
        ) = create_executor()

        execution = create_paused_execution(
            execution_id="execution-shared-context",
            task_id="task-shared-context",
            checkpoint_id="checkpoint-shared-context",
        )

        checkpoint = create_checkpoint(
            checkpoint_id="checkpoint-shared-context",
            runtime_id="runtime-shared-context",
            task_id="task-shared-context",
        )

        checkpoint.shared_context.set(
            "research.status",
            "completed",
        )

        checkpoint.shared_context.set(
            "risk.score",
            0.25,
        )

        await execution_store.save(
            execution.snapshot()
        )

        await checkpoint_store.save(
            checkpoint.checkpoint_id,
            checkpoint,
        )

        handle = await executor.recover_persisted_execution(
            execution_id=execution.execution_id
        )

        try:
            assert (
                handle.runtime_context.shared_context.get(
                    "research.status"
                )
                == "completed"
            )

            assert (
                handle.runtime_context.shared_context.get(
                    "risk.score"
                )
                == 0.25
            )
        finally:
            await handle.close()

    run_async(scenario())


def test_recover_persisted_execution_creates_new_trace():
    async def scenario():
        (
            executor,
            execution_store,
            _,
            checkpoint_store,
            _,
        ) = create_executor()

        execution = create_paused_execution(
            execution_id="execution-trace",
            task_id="task-trace",
            checkpoint_id="checkpoint-trace",
        )

        checkpoint = create_checkpoint(
            checkpoint_id="checkpoint-trace",
            runtime_id="runtime-trace",
            task_id="task-trace",
        )

        await execution_store.save(
            execution.snapshot()
        )

        await checkpoint_store.save(
            checkpoint.checkpoint_id,
            checkpoint,
        )

        handle = await executor.recover_persisted_execution(
            execution_id=execution.execution_id
        )

        try:
            assert (
                handle.runtime_context.trace.trace.trace_id
                is not None
            )

            assert (
                handle.runtime_context.trace.trace.trace_id
                != checkpoint.runtime_id
            )

            assert (
                handle.runtime_context.trace.trace.all_spans()[0].name
                == "agent.resume"
            )
        finally:
            await handle.close()

    run_async(scenario())


def test_recover_execution_does_not_require_application():
    async def scenario():
        (
            executor,
            _,
            _,
            _,
            _,
        ) = create_executor()

        checkpoint = create_checkpoint(
            checkpoint_id="checkpoint-low-level",
            runtime_id="runtime-low-level",
            task_id="task-low-level",
        )

        handle = await executor.recover_execution(
            checkpoint=checkpoint
        )

        try:
            assert (
                handle.runtime_id
                == "runtime-low-level"
            )

            assert (
                handle.execution.task_id
                == "task-low-level"
            )

            assert (
                handle.execution.status
                == ExecutionStatus.PAUSED
            )
        finally:
            await handle.close()

    run_async(scenario())