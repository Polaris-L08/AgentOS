from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from agents import AgentResult, BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.application.application import AgentApplication
from runtime.application.application_executor import (
    ApplicationExecutor,
)
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.checkpoint.checkpoint import (
    AgentCheckpoint,
    Checkpoint,
)
from runtime.checkpoint.memory_checkpoint_store import (
    MemoryCheckpointStore,
)
from runtime.context.agent_execution_context import (
    AgentExecutionContext,
)
from runtime.context.shared_context import SharedContext
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_handle import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.execution.execution_state import (
    ExecutionState,
    ExecutionStatus,
)
from runtime.persistence.in_memory_execution_store import (
    InMemoryExecutionStore,
)
from runtime.persistence.in_memory_task_store import (
    InMemoryTaskStore,
)
from runtime.persistence.task_store import TaskStore
from runtime.tracing.trace_recorder import TraceRecorder


class RecoverableAgent(BaseAgent):
    """
    Deterministic Agent used by Lesson19 recovery tests.

    The Agent records the durable execution information restored
    after the simulated process restart.
    """

    def __init__(
        self,
        identity: AgentIdentity | None = None,
    ) -> None:
        super().__init__(
            identity=(
                identity
                or AgentIdentity(
                    agent_id="recoverable-agent-001",
                    agent_type="recovery-test",
                    name="RecoverableAgent",
                )
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

        self.received_task_ids.append(
            task.task_id
        )

        self.received_runtime_ids.append(
            agent_execution_context
            .runtime_context
            .runtime_id
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
                    agent_execution_context
                    .loop.step_count
                ),
            },
            metadata={
                "agent_id": self.identity.agent_id,
            },
        )


@dataclass
class ProcessRuntime:
    """
    Runtime resources representing one process.

    Persistence stores are shared between Process A and Process B
    to simulate durable storage surviving a process crash.
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
    Create one independent runtime process.

    Runtime components are recreated for every process.

    Persistence stores may be shared between processes.
    """

    actual_execution_store = (
        execution_store
        or InMemoryExecutionStore()
    )

    actual_task_store = (
        task_store
        or InMemoryTaskStore()
    )

    actual_checkpoint_store = (
        checkpoint_store
        or MemoryCheckpointStore()
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
            else _raise_agent_not_found(agent_id)
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


def create_application(
    *,
    execution_store: InMemoryExecutionStore,
    task_store: TaskStore,
    checkpoint_store: MemoryCheckpointStore,
    agent: RecoverableAgent,
) -> AgentApplication:
    """
    Create a real AgentApplication representing one process.

    This is used by the Application-level recovery test.
    """

    return AgentApplication(
        application_id="lesson19-recovery-app",
        name="Lesson19 Recovery Application",
        agent_runtime=AgentRuntime(),
        execution_runtime=ExecutionRuntime(
            trace_recorder=TraceRecorder(),
        ),
        agents=[agent],
        execution_store=execution_store,
        task_store=task_store,
        checkpoint_store=checkpoint_store,
    )


def _raise_agent_not_found(
    agent_id: str,
):
    raise KeyError(
        f"Agent not found in Application: {agent_id}"
    )


def create_execution_state(
    *,
    execution_id: str,
    task_id: str,
    checkpoint_id: str,
    entry_agent_id: str,
) -> ExecutionState:
    """
    Create durable ExecutionState representing a paused
    Execution after a crash.

    The orchestration entry Agent is stored in Execution metadata.
    """

    return ExecutionState(
        execution_id=execution_id,
        status=ExecutionStatus.PAUSED,
        task_id=task_id,
        session_id=None,
        current_checkpoint_id=checkpoint_id,
        metadata={
            "orchestrator_agent_id": entry_agent_id,
            "source": "lesson19-crash-restart-test",
        },
    )


def create_checkpoint(
    *,
    checkpoint_id: str,
    runtime_id: str,
    task_id: str,
    agent_id: str = "recoverable-agent-001",
) -> Checkpoint:
    """
    Create a durable Checkpoint containing one AgentCheckpoint.
    """

    agent = RecoverableAgent(
        identity=AgentIdentity(
            agent_id=agent_id,
            agent_type="recovery-test",
            name="RecoverableAgent",
        )
    )

    runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    runtime_context = runtime.create_context()

    agent_execution_context = (
        AgentExecutionContext.create(
            runtime_context=runtime_context,
            agent=agent,
        )
    )

    agent_execution_context.loop.step_count = 3

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
    Lesson19 keeps the low-level recovery contract:

        Process A
            ↓
        Execution + Checkpoint
            ↓
        Crash
            ↓
        Process B
            ↓
        recover_persisted_execution()
            ↓
        ExecutionHandle

    Logical Execution identity and RuntimeContext identity
    must both survive restart.
    """

    task = TaskRequest(
        task_id="lesson19-task-001",
        user_input="Analyze NVIDIA stock risk",
    )

    execution_id = "lesson19-execution-001"
    checkpoint_id = "lesson19-checkpoint-001"
    runtime_id = "lesson19-runtime-001"
    agent_id = "recoverable-agent-001"

    process_a = create_process()

    await process_a.task_store.save(task)

    await process_a.execution_store.save(
        create_execution_state(
            execution_id=execution_id,
            task_id=task.task_id,
            checkpoint_id=checkpoint_id,
            entry_agent_id=agent_id,
        )
    )

    checkpoint = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id=runtime_id,
        task_id=task.task_id,
        agent_id=agent_id,
    )

    await process_a.checkpoint_store.save(
        checkpoint_id,
        checkpoint,
    )

    execution_store = process_a.execution_store
    task_store = process_a.task_store
    checkpoint_store = process_a.checkpoint_store

    del process_a

    process_b = create_process(
        execution_store=execution_store,
        task_store=task_store,
        checkpoint_store=checkpoint_store,
    )

    handle = await (
        process_b.executor
        .recover_persisted_execution(
            execution_id=execution_id,
        )
    )

    try:
        assert isinstance(
            handle,
            ExecutionHandle,
        )

        assert (
            handle.execution_id
            == execution_id
        )

        assert (
            handle.runtime_id
            == runtime_id
        )

        assert (
            handle.execution_id
            != handle.runtime_id
        )

        assert (
            handle.execution.task_id
            == task.task_id
        )

        assert (
            handle.execution.current_checkpoint_id
            == checkpoint_id
        )

        assert (
            handle.execution.status
            == ExecutionStatus.PAUSED
        )

        assert (
            handle.runtime_context.runtime_id
            == runtime_id
        )

        assert (
            handle.runtime_context
            .shared_context
            .get("recovery.marker")
            == "checkpoint-created-before-crash"
        )

        assert (
            handle.runtime_context
            .trace
            .trace
            .trace_id
            is not None
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
async def test_application_resume_execution_reconstructs_complete_execution() -> None:
    """
    Lesson19 main acceptance test.

    Process A
        ↓
    TaskStore
        +
    ExecutionStore
        +
    CheckpointStore
        ↓
    Crash
        ↓
    Process B
        ↓
    AgentApplication.resume_execution()
        ↓
    TaskRequest reconstruction
        ↓
    Execution reconstruction
        ↓
    Checkpoint reconstruction
        ↓
    Orchestrator.resume()
        ↓
    AgentRuntime
        ↓
    TaskResult
    """

    task = TaskRequest(
        task_id="lesson19-task-002",
        user_input="Continue NVIDIA risk analysis",
    )

    execution_id = "lesson19-execution-002"
    checkpoint_id = "lesson19-checkpoint-002"
    runtime_id = "lesson19-runtime-002"
    agent_id = "recoverable-agent-001"

    process_a = create_process()

    await process_a.task_store.save(task)

    await process_a.execution_store.save(
        create_execution_state(
            execution_id=execution_id,
            task_id=task.task_id,
            checkpoint_id=checkpoint_id,
            entry_agent_id=agent_id,
        )
    )

    checkpoint = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id=runtime_id,
        task_id=task.task_id,
        agent_id=agent_id,
    )

    await process_a.checkpoint_store.save(
        checkpoint_id,
        checkpoint,
    )

    execution_store = process_a.execution_store
    task_store = process_a.task_store
    checkpoint_store = process_a.checkpoint_store

    del process_a

    recovered_agent = RecoverableAgent()

    process_b = create_application(
        execution_store=execution_store,
        task_store=task_store,
        checkpoint_store=checkpoint_store,
        agent=recovered_agent,
    )

    await process_b.initialize()
    await process_b.start()

    try:
        result = await process_b.resume_execution(
            execution_id=execution_id,
        )

        assert result.success is True

        assert (
            result.metadata["task_id"]
            == task.task_id
        )

        assert (
            result.metadata["agent_id"]
            == agent_id
        )

        assert (
            recovered_agent.invocation_count
            == 1
        )

        assert (
            recovered_agent.received_task_ids
            == [task.task_id]
        )

        assert (
            recovered_agent.received_runtime_ids
            == [runtime_id]
        )

        assert (
            recovered_agent.received_step_counts
            == [3]
        )

        persisted = (
            await execution_store.load(
                execution_id
            )
        )

        assert persisted is not None

        assert (
            persisted.status
            == ExecutionStatus.COMPLETED
        )

    finally:
        await process_b.stop()


@pytest.mark.asyncio
async def test_application_resume_execution_rejects_missing_task() -> None:
    """
    Application-level recovery must fail when the durable
    TaskRequest is missing.
    """

    task_id = "lesson19-missing-task"
    execution_id = "lesson19-execution-missing-task"
    checkpoint_id = "lesson19-checkpoint-missing-task"
    runtime_id = "lesson19-runtime-missing-task"
    agent_id = "recoverable-agent-001"

    execution_store = InMemoryExecutionStore()
    task_store = InMemoryTaskStore()
    checkpoint_store = MemoryCheckpointStore()

    await execution_store.save(
        create_execution_state(
            execution_id=execution_id,
            task_id=task_id,
            checkpoint_id=checkpoint_id,
            entry_agent_id=agent_id,
        )
    )

    checkpoint = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id=runtime_id,
        task_id=task_id,
        agent_id=agent_id,
    )

    await checkpoint_store.save(
        checkpoint_id,
        checkpoint,
    )

    application = create_application(
        execution_store=execution_store,
        task_store=task_store,
        checkpoint_store=checkpoint_store,
        agent=RecoverableAgent(),
    )

    await application.initialize()
    await application.start()

    try:
        with pytest.raises(
            ApplicationLifecycleError,
            match="Task not found for Execution",
        ):
            await application.resume_execution(
                execution_id=execution_id,
            )
    finally:
        await application.stop()


@pytest.mark.asyncio
async def test_application_resume_execution_rejects_task_checkpoint_mismatch() -> None:
    """
    Execution and Checkpoint must refer to the same logical Task.
    """

    execution_id = (
        "lesson19-execution-task-mismatch"
    )
    checkpoint_id = (
        "lesson19-checkpoint-task-mismatch"
    )

    execution_store = InMemoryExecutionStore()
    task_store = InMemoryTaskStore()
    checkpoint_store = MemoryCheckpointStore()

    task = TaskRequest(
        task_id="task-execution",
        user_input="test mismatch",
    )

    await task_store.save(task)

    await execution_store.save(
        create_execution_state(
            execution_id=execution_id,
            task_id=task.task_id,
            checkpoint_id=checkpoint_id,
            entry_agent_id=(
                "recoverable-agent-001"
            ),
        )
    )

    checkpoint = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id="lesson19-runtime-mismatch",
        task_id="task-checkpoint",
    )

    await checkpoint_store.save(
        checkpoint_id,
        checkpoint,
    )

    application = create_application(
        execution_store=execution_store,
        task_store=task_store,
        checkpoint_store=checkpoint_store,
        agent=RecoverableAgent(),
    )

    await application.initialize()
    await application.start()

    try:
        with pytest.raises(
            ApplicationLifecycleError,
            match=(
                "Checkpoint task_id does not match "
                "Execution task_id"
            ),
        ):
            await application.resume_execution(
                execution_id=execution_id,
            )
    finally:
        await application.stop()


@pytest.mark.asyncio
async def test_application_resume_execution_rejects_missing_entry_agent() -> None:
    """
    Durable recovery must not silently select another Agent when
    the persisted orchestration entry Agent is missing.
    """

    task = TaskRequest(
        task_id="lesson19-task-missing-entry-agent",
        user_input="test missing orchestration entry",
    )

    execution_id = (
        "lesson19-execution-missing-entry-agent"
    )
    checkpoint_id = (
        "lesson19-checkpoint-missing-entry-agent"
    )

    execution_store = InMemoryExecutionStore()
    task_store = InMemoryTaskStore()
    checkpoint_store = MemoryCheckpointStore()

    await task_store.save(task)

    await execution_store.save(
        create_execution_state(
            execution_id=execution_id,
            task_id=task.task_id,
            checkpoint_id=checkpoint_id,
            entry_agent_id=(
                "agent-does-not-exist"
            ),
        )
    )

    checkpoint = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id="lesson19-runtime-missing-agent",
        task_id=task.task_id,
        agent_id="agent-does-exist",
    )

    await checkpoint_store.save(
        checkpoint_id,
        checkpoint,
    )

    application = create_application(
        execution_store=execution_store,
        task_store=task_store,
        checkpoint_store=checkpoint_store,
        agent=RecoverableAgent(),
    )

    await application.initialize()
    await application.start()

    try:
        with pytest.raises(
                ApplicationLifecycleError,
                match=(
                        "Checkpoint does not contain the persisted "
                        "orchestration entry Agent"
                ),
        ):
            await application.resume_execution(
                execution_id=execution_id,
            )
    finally:
        await application.stop()