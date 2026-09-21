from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from agents import AgentResult, BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.application.application_executor import ApplicationExecutor
from runtime.checkpoint.checkpoint import AgentCheckpoint, Checkpoint
from runtime.checkpoint.memory_checkpoint_store import MemoryCheckpointStore
from runtime.context.agent_execution_context import AgentExecutionContext
from runtime.context.context_state import ContextState
from runtime.context.shared_context import SharedContext
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_handle import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.execution.execution_state import ExecutionState, ExecutionStatus
from runtime.persistence.in_memory_execution_store import InMemoryExecutionStore
from runtime.persistence.in_memory_task_store import InMemoryTaskStore
from runtime.persistence.task_store import TaskStore
from runtime.tracing.trace_recorder import TraceRecorder


class RecoverableAgent(BaseAgent):
    """
    Deterministic Agent used by Lesson18 recovery integration tests.

    The Agent records the TaskRequest, RuntimeContext and restored
    execution-local state it receives during resumed execution.
    """

    def __init__(
        self,
        identity: AgentIdentity | None = None,
    ) -> None:
        super().__init__(
            identity=identity
            or AgentIdentity(
                agent_id="recoverable-agent-001",
                agent_type="recovery-test",
                name="RecoverableAgent",
            )
        )

        self.invocation_count = 0
        self.received_task_ids: list[str] = []
        self.received_runtime_ids: list[str] = []
        self.received_step_counts: list[int] = []

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:
        self.invocation_count += 1

        self.received_task_ids.append(task.task_id)

        self.received_runtime_ids.append(
            agent_execution_context.runtime_context.runtime_id
        )

        self.received_step_counts.append(
            agent_execution_context.loop.step_count
        )

        return AgentResult(
            success=True,
            output={
                "task_id": task.task_id,
                "runtime_id": (
                    agent_execution_context
                    .runtime_context
                    .runtime_id
                ),
                "step_count": (
                    agent_execution_context.loop.step_count
                ),
            },
            metadata={
                "agent_id": self.identity.agent_id,
            },
        )


@dataclass
class ProcessRuntime:
    """
    Runtime resources representing one application process.

    The persistence stores are intentionally shared between Process A
    and Process B to simulate durable storage surviving a process crash.
    """

    execution_store: InMemoryExecutionStore
    task_store: TaskStore
    checkpoint_store: MemoryCheckpointStore
    execution_runtime: ExecutionRuntime
    agent_runtime: AgentRuntime
    agent: RecoverableAgent
    executor: ApplicationExecutor


def create_process(
    *,
    execution_store: InMemoryExecutionStore | None = None,
    task_store: TaskStore | None = None,
    checkpoint_store: MemoryCheckpointStore | None = None,
) -> ProcessRuntime:
    """
    Create one independent runtime representing one process.

    Runtime components are recreated for every process.
    Persistence stores can be shared to represent durable storage.
    """

    actual_execution_store = (
        execution_store or InMemoryExecutionStore()
    )

    actual_task_store = (
        task_store or InMemoryTaskStore()
    )

    actual_checkpoint_store = (
        checkpoint_store or MemoryCheckpointStore()
    )

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    agent_runtime = AgentRuntime()

    agent = RecoverableAgent()

    application = SimpleNamespace(
        execution_store=actual_execution_store,
        task_store=actual_task_store,
        checkpoint_store=actual_checkpoint_store,
        agent_runtime=agent_runtime,
        agents=(agent,),
        get_agent=lambda agent_id: (
            agent
            if agent.identity.agent_id == agent_id
            else (_raise_agent_not_found(agent_id))
        ),
    )

    executor = ApplicationExecutor(
        application=application,
        execution_runtime=execution_runtime,
    )

    return ProcessRuntime(
        execution_store=actual_execution_store,
        task_store=actual_task_store,
        checkpoint_store=actual_checkpoint_store,
        execution_runtime=execution_runtime,
        agent_runtime=agent_runtime,
        agent=agent,
        executor=executor,
    )


def _raise_agent_not_found(agent_id: str):
    raise KeyError(
        f"Agent not found in Application: {agent_id}"
    )


def create_execution_state(
    *,
    execution_id: str,
    task_id: str,
    checkpoint_id: str,
) -> ExecutionState:
    """
    Create the durable ExecutionState representing a paused execution.
    """

    return ExecutionState(
        execution_id=execution_id,
        status=ExecutionStatus.PAUSED,
        task_id=task_id,
        session_id=None,
        current_checkpoint_id=checkpoint_id,
        metadata={
            "source": "lesson18-crash-restart-test",
        },
    )


def create_checkpoint(
    *,
    checkpoint_id: str,
    runtime_id: str,
    task_id: str,
) -> Checkpoint:
    """
    Create a durable Checkpoint containing one AgentCheckpoint.

    The AgentCheckpoint represents execution-local state that must be
    restored into the new AgentExecutionContext after restart.
    """

    agent = RecoverableAgent()

    runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    runtime_context = runtime.create_context()

    agent_execution_context = AgentExecutionContext.create(
        runtime_context=runtime_context,
        agent=agent,
    )

    agent_execution_context.loop.step_count = 3

    # agent_execution_context.state.set(
    #     "recovery.step",
    #     "research-completed",
    # )

    agent_checkpoint = AgentCheckpoint(
        agent_id=agent.identity.agent_id,
        status="RUNNING",
        state=agent_execution_context.state,
        loop=agent_execution_context.loop,
    )

    return Checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id=runtime_id,
        shared_context=SharedContext(
            data={
                "recovery.marker": (
                    "checkpoint-created-before-crash"
                ),
            }
        ),
        agents={
            agent.identity.agent_id: agent_checkpoint,
        },
        task_id=task_id,
    )


@pytest.mark.asyncio
async def test_crash_restart_recovery_restores_persisted_execution() -> None:
    """
    Lesson18 acceptance:

        Process A
            Task
              ↓
            Execution
              ↓
            Checkpoint
              ↓
            Persistence

        Process A crashes

        Process B
            ↓
        recover_persisted_execution()
            ↓
        ExecutionHandle

    The logical Execution identity and RuntimeContext identity must
    be restored from durable state.
    """

    task = TaskRequest(
        task_id="lesson18-task-001",
        user_input="Analyze NVIDIA stock risk",
    )

    execution_id = "lesson18-execution-001"
    checkpoint_id = "lesson18-checkpoint-001"
    runtime_id = "lesson18-runtime-001"

    # ---------------------------------------------------------------
    # Process A
    # ---------------------------------------------------------------

    process_a = create_process()

    await process_a.task_store.save(task)

    await process_a.execution_store.save(
        create_execution_state(
            execution_id=execution_id,
            task_id=task.task_id,
            checkpoint_id=checkpoint_id,
        )
    )

    checkpoint = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id=runtime_id,
        task_id=task.task_id,
    )

    await process_a.checkpoint_store.save(
        checkpoint_id,
        checkpoint,
    )

    # ---------------------------------------------------------------
    # Process crash
    #
    # Only persistence survives.
    # Runtime objects from Process A are discarded.
    # ---------------------------------------------------------------

    execution_store = process_a.execution_store
    task_store = process_a.task_store
    checkpoint_store = process_a.checkpoint_store

    del process_a

    # ---------------------------------------------------------------
    # Process B
    # ---------------------------------------------------------------

    process_b = create_process(
        execution_store=execution_store,
        task_store=task_store,
        checkpoint_store=checkpoint_store,
    )

    handle = await process_b.executor.recover_persisted_execution(
        execution_id=execution_id,
    )

    try:
        assert isinstance(handle, ExecutionHandle)

        # Logical Execution identity survives restart.
        assert handle.execution_id == execution_id

        # Runtime identity is restored from Checkpoint.
        assert handle.runtime_id == runtime_id

        # They are different identity domains.
        assert handle.execution_id != handle.runtime_id

        # Execution is reconstructed from ExecutionState.
        assert handle.execution.task_id == task.task_id

        assert (
            handle.execution.current_checkpoint_id
            == checkpoint_id
        )

        assert (
            handle.execution.status
            == ExecutionStatus.PAUSED
        )

        # RuntimeContext is reconstructed from Checkpoint.
        assert (
            handle.runtime_context.runtime_id
            == runtime_id
        )

        assert (
            handle.runtime_context.shared_context.get(
                "recovery.marker"
            )
            == "checkpoint-created-before-crash"
        )

        # Recovery creates a new trace.
        assert (
            handle.runtime_context.trace.trace.trace_id
            is not None
        )

        assert (
            handle.runtime_context.trace.trace.trace_id
            != runtime_id
        )

        assert (
            handle.runtime_context
            .trace
            .trace
            .all_spans()[0]
            .name
            == "agent.resume"
        )
    finally:
        await handle.close()


@pytest.mark.asyncio
async def test_crash_restart_recovery_loads_original_task() -> None:
    """
    TaskRequest is durable input of the logical Execution.

    recover_persisted_execution() intentionally does not reconstruct
    TaskRequest itself. The recovery integration therefore loads the
    original TaskRequest from TaskStore.
    """

    task = TaskRequest(
        task_id="lesson18-task-002",
        user_input="Determine current NVIDIA risk",
    )

    process_a = create_process()

    await process_a.task_store.save(task)

    # Simulate Process A disappearing.
    task_store = process_a.task_store
    del process_a

    process_b = create_process(
        task_store=task_store,
    )

    recovered_task = await process_b.task_store.load(
        task.task_id,
    )

    assert recovered_task is not None
    assert recovered_task.task_id == task.task_id
    assert recovered_task.user_input == task.user_input


@pytest.mark.asyncio
async def test_crash_restart_recovery_resumes_agent_from_checkpoint() -> None:
    """
    Full Lesson18 Agent resume path.

        Process A
            ↓
        Checkpoint
            ↓
        Crash
            ↓
        Process B
            ↓
        recover_persisted_execution()
            ↓
        Load TaskRequest from TaskStore
            ↓
        recover_agent_execution()
            ↓
        restore AgentExecutionContext
            ↓
        AgentRuntime.execute()
    """

    task = TaskRequest(
        task_id="lesson18-task-003",
        user_input="Continue NVIDIA risk analysis",
    )

    execution_id = "lesson18-execution-003"
    checkpoint_id = "lesson18-checkpoint-003"
    runtime_id = "lesson18-runtime-003"

    # ---------------------------------------------------------------
    # Process A
    # ---------------------------------------------------------------

    process_a = create_process()

    await process_a.task_store.save(task)

    await process_a.execution_store.save(
        create_execution_state(
            execution_id=execution_id,
            task_id=task.task_id,
            checkpoint_id=checkpoint_id,
        )
    )

    checkpoint = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id=runtime_id,
        task_id=task.task_id,
    )

    await process_a.checkpoint_store.save(
        checkpoint_id,
        checkpoint,
    )

    # Capture only the durable stores.
    execution_store = process_a.execution_store
    task_store = process_a.task_store
    checkpoint_store = process_a.checkpoint_store

    del process_a

    # ---------------------------------------------------------------
    # Process B
    # ---------------------------------------------------------------

    process_b = create_process(
        execution_store=execution_store,
        task_store=task_store,
        checkpoint_store=checkpoint_store,
    )

    # Step 1:
    # Recover logical Execution + RuntimeContext.
    handle = await process_b.executor.recover_persisted_execution(
        execution_id=execution_id,
    )

    try:
        assert handle.execution_id == execution_id
        assert handle.runtime_id == runtime_id

        # Step 2:
        # Recover the original TaskRequest.
        recovered_task = await process_b.task_store.load(
            task.task_id,
        )

        assert recovered_task is not None
        assert recovered_task.task_id == task.task_id
        assert recovered_task.user_input == task.user_input

        # Step 3:
        # Load the durable Checkpoint.
        recovered_checkpoint = (
            await process_b.checkpoint_store.load(
                checkpoint_id,
            )
        )

        assert recovered_checkpoint is not None
        assert (
            recovered_checkpoint.runtime_id
            == runtime_id
        )

        # Step 4:
        # Resume the Agent using the existing API.
        result = await process_b.executor.recover_agent_execution(
            checkpoint=recovered_checkpoint,
            agent_id=process_b.agent.identity.agent_id,
            task=recovered_task,
        )

        assert result.success is True

        assert (
            result.output["task_id"]
            == task.task_id
        )

        assert (
            result.output["runtime_id"]
            == runtime_id
        )

        # The AgentExecutionContext was restored from checkpoint.
        assert (
            result.output["step_count"]
            == 3
        )

        assert process_b.agent.invocation_count == 1

        assert (
            process_b.agent.received_task_ids
            == [task.task_id]
        )

        assert (
            process_b.agent.received_runtime_ids
            == [runtime_id]
        )

        assert (
            process_b.agent.received_step_counts
            == [3]
        )

    finally:
        # recover_agent_execution() creates and closes its own handle.
        # This handle belongs to the persisted Execution recovery above.
        await handle.close()


@pytest.mark.asyncio
async def test_crash_restart_recovery_rejects_missing_task() -> None:
    """
    The durable TaskRequest is required by the Agent resume phase.

    A missing TaskStore entry must prevent Agent recovery.
    """

    task_id = "lesson18-missing-task"

    execution_id = "lesson18-execution-missing-task"
    checkpoint_id = "lesson18-checkpoint-missing-task"

    process = create_process()

    await process.execution_store.save(
        create_execution_state(
            execution_id=execution_id,
            task_id=task_id,
            checkpoint_id=checkpoint_id,
        )
    )

    checkpoint = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id="lesson18-runtime-missing-task",
        task_id=task_id,
    )

    await process.checkpoint_store.save(
        checkpoint_id,
        checkpoint,
    )

    # The Execution and Checkpoint can be recovered independently.
    handle = await process.executor.recover_persisted_execution(
        execution_id=execution_id,
    )

    try:
        assert handle.execution_id == execution_id
    finally:
        await handle.close()

    # But the Agent resume phase cannot continue without TaskRequest.
    recovered_task = await process.task_store.load(
        task_id,
    )

    assert recovered_task is None


@pytest.mark.asyncio
async def test_crash_restart_recovery_rejects_task_checkpoint_mismatch() -> None:
    """
    Execution and Checkpoint must refer to the same logical Task.

    This validation already belongs to recover_persisted_execution().
    Lesson18 verifies it as part of the restart boundary.
    """

    execution_id = "lesson18-execution-task-mismatch"
    checkpoint_id = "lesson18-checkpoint-task-mismatch"

    process = create_process()

    await process.execution_store.save(
        create_execution_state(
            execution_id=execution_id,
            task_id="task-execution",
            checkpoint_id=checkpoint_id,
        )
    )

    checkpoint = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id="lesson18-runtime-task-mismatch",
        task_id="task-checkpoint",
    )

    await process.checkpoint_store.save(
        checkpoint_id,
        checkpoint,
    )

    from runtime.application.application_lifecycle import (
        ApplicationLifecycleError,
    )

    with pytest.raises(
        ApplicationLifecycleError,
        match=(
            "Checkpoint task_id does not match "
            "Execution task_id"
        ),
    ):
        await process.executor.recover_persisted_execution(
            execution_id=execution_id,
        )