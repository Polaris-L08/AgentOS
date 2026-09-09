import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from agents.agent_result import AgentResult
from models.task_request import TaskRequest
from runtime.application import AgentApplication
from runtime.checkpoint.checkpoint_coordinator import CheckpointCoordinator
from runtime.context.agent_execution_context import AgentExecutionContext
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_handle import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class RecoveryTestAgent(BaseAgent):

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output=f"processed: {task.user_input}",
        )


def create_agent(
    agent_id: str = "agent-001",
) -> RecoveryTestAgent:
    return RecoveryTestAgent(
        identity=AgentIdentity(
            agent_id=agent_id,
            agent_type="recovery-test",
            name=agent_id,
        )
    )


def create_application(
    agent: BaseAgent | None = None,
) -> AgentApplication:
    agent_runtime = AgentRuntime()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    return AgentApplication(
        application_id="app-001",
        name="Recovery Test Application",
        agent_runtime=agent_runtime,
        execution_runtime=execution_runtime,
        agents=[agent or create_agent()],
    )


def create_checkpoint_from_execution(
    execution_handle: ExecutionHandle,
    agent: BaseAgent,
):
    coordinator = CheckpointCoordinator()

    agent_execution_context = AgentExecutionContext.create(
        runtime_context=execution_handle.runtime_context,
        agent=agent,
    )

    return coordinator.create_checkpoint(
        runtime_context=execution_handle.runtime_context,
        agent_execution_contexts={
            agent.identity.agent_id: agent_execution_context,
        },
        task_id="task-recovery-001",
    )


@pytest.mark.asyncio
async def test_application_executor_recovers_execution_handle():
    """
    ApplicationExecutor should recover an ExecutionHandle from
    a durable Checkpoint.

    ApplicationExecutor must delegate recovery to
    ExecutionRuntime.resume_execution().
    """

    application = create_application()

    await application.initialize()
    await application.start()

    original_handle = application.execution_runtime.create_execution()

    checkpoint = create_checkpoint_from_execution(
        execution_handle=original_handle,
        agent=application.agents[0],
    )

    recovered_handle = await application._executor.recover_execution(
        checkpoint
    )

    try:
        assert isinstance(
            recovered_handle,
            ExecutionHandle,
        )

        assert recovered_handle.closed is False

        assert (
            recovered_handle.execution_id
            == checkpoint.runtime_id
        )

    finally:
        await recovered_handle.close()
        await original_handle.close()
        await application.stop()


@pytest.mark.asyncio
async def test_application_recovery_preserves_execution_identity():
    """
    Recovery must preserve the original Execution identity.

    Checkpoint.runtime_id
        ==
    recovered ExecutionHandle.execution_id
    """

    application = create_application()

    await application.initialize()
    await application.start()

    original_handle = application.execution_runtime.create_execution()

    checkpoint = create_checkpoint_from_execution(
        execution_handle=original_handle,
        agent=application.agents[0],
    )

    recovered_handle = await application._executor.recover_execution(
        checkpoint
    )

    try:
        assert (
            recovered_handle.runtime_context.runtime_id
            == original_handle.runtime_context.runtime_id
        )

        assert (
            recovered_handle.execution_id
            == original_handle.execution_id
        )

    finally:
        await recovered_handle.close()
        await original_handle.close()
        await application.stop()


@pytest.mark.asyncio
async def test_application_recovery_creates_new_trace():
    """
    Execution identity survives recovery, but Trace identity does not.

    This prevents a recovered execution from pretending that it is
    the same tracing lifecycle as the original execution.
    """

    application = create_application()

    await application.initialize()
    await application.start()

    original_handle = application.execution_runtime.create_execution()

    original_trace_id = (
        original_handle
        .runtime_context
        .trace
        .trace
        .trace_id
    )

    checkpoint = create_checkpoint_from_execution(
        execution_handle=original_handle,
        agent=application.agents[0],
    )

    recovered_handle = await application._executor.recover_execution(
        checkpoint
    )

    try:
        recovered_trace_id = (
            recovered_handle
            .runtime_context
            .trace
            .trace
            .trace_id
        )

        assert recovered_trace_id != original_trace_id

    finally:
        await recovered_handle.close()
        await original_handle.close()
        await application.stop()


@pytest.mark.asyncio
async def test_application_recovery_restores_shared_context():
    """
    SharedContext belongs to the Execution-level durable state.

    Recovery must reconstruct RuntimeContext with the SharedContext
    contained in the Checkpoint.
    """

    application = create_application()

    await application.initialize()
    await application.start()

    original_handle = application.execution_runtime.create_execution()

    original_shared_context = (
        original_handle
        .runtime_context
        .shared_context
    )

    original_shared_context.set(
        "research_topic",
        "NVIDIA",
    )

    original_shared_context.set(
        "risk_level",
        "high",
    )

    checkpoint = create_checkpoint_from_execution(
        execution_handle=original_handle,
        agent=application.agents[0],
    )

    recovered_handle = await application._executor.recover_execution(
        checkpoint
    )

    try:
        recovered_shared_context = (
            recovered_handle
            .runtime_context
            .shared_context
        )

        assert (
            recovered_shared_context.get("research_topic")
            == "NVIDIA"
        )

        assert (
            recovered_shared_context.get("risk_level")
            == "high"
        )

    finally:
        await recovered_handle.close()
        await original_handle.close()
        await application.stop()


@pytest.mark.asyncio
async def test_application_recovered_execution_can_restore_agent_context():
    """
    Application-level Execution recovery and Agent-level recovery
    must compose correctly.

    The ApplicationExecutor restores the ExecutionHandle.

    AgentRuntime remains responsible for restoring the
    AgentExecutionContext from the corresponding AgentCheckpoint.
    """

    agent = create_agent()

    application = create_application(
        agent=agent,
    )

    await application.initialize()
    await application.start()

    original_handle = application.execution_runtime.create_execution()

    coordinator = CheckpointCoordinator()

    original_agent_execution_context = AgentExecutionContext.create(
        runtime_context=original_handle.runtime_context,
        agent=agent,
    )

    original_agent_execution_context.loop.step_count = 7
    original_agent_execution_context.loop.reflection_count = 2

    original_agent_execution_context.state.model_extra

    checkpoint = coordinator.create_checkpoint(
        runtime_context=original_handle.runtime_context,
        agent_execution_contexts={
            agent.identity.agent_id: original_agent_execution_context,
        },
        task_id="task-recovery-001",
    )

    recovered_handle = await application._executor.recover_execution(
        checkpoint
    )

    try:
        agent_checkpoint = checkpoint.agents[
            agent.identity.agent_id
        ]

        restored_agent_execution_context = (
            application.agent_runtime.restore_execution_context(
                runtime_context=recovered_handle.runtime_context,
                agent=agent,
                checkpoint=agent_checkpoint,
            )
        )

        assert (
            restored_agent_execution_context.runtime_context
            is recovered_handle.runtime_context
        )

        assert (
            restored_agent_execution_context.agent_identity
            is agent.identity
        )

        assert (
            restored_agent_execution_context.agent_context
            is agent.context
        )

        assert (
            restored_agent_execution_context.memory
            is agent.memory
        )

        assert (
            restored_agent_execution_context.loop.step_count
            == 7
        )

        assert (
            restored_agent_execution_context.loop.reflection_count
            == 2
        )

    finally:
        await recovered_handle.close()
        await original_handle.close()
        await application.stop()


@pytest.mark.asyncio
async def test_application_recovered_execution_handle_can_be_closed():
    """
    Application recovery returns an open ExecutionHandle.

    The caller owns the recovered handle and must close it.
    """

    application = create_application()

    await application.initialize()
    await application.start()

    original_handle = application.execution_runtime.create_execution()

    checkpoint = create_checkpoint_from_execution(
        execution_handle=original_handle,
        agent=application.agents[0],
    )

    recovered_handle = await application._executor.recover_execution(
        checkpoint
    )

    assert recovered_handle.closed is False

    await recovered_handle.close()

    assert recovered_handle.closed is True

    # Closing a recovered execution is idempotent.
    await recovered_handle.close()

    assert recovered_handle.closed is True

    await original_handle.close()
    await application.stop()