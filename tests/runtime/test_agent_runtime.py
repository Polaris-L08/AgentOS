from __future__ import annotations

import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from agents.research.research_agent import ResearchAgent
from models.task_request import TaskRequest
from runtime.checkpoint.checkpoint import AgentCheckpoint
from runtime.context import AgentExecutionContext
from runtime.context.context_state import ContextState
from runtime.context.runtime_context import RuntimeContext
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.loop.loop_state import LoopState
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    """
    Simple Agent used for AgentRuntime testing.
    """

    def __init__(self, identity: AgentIdentity):
        super().__init__(identity)
        self.execution_context: AgentExecutionContext | None = None
        self.execution_count = 0

    async def run(
        self,
        task,
        agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:

        self.execution_context = agent_execution_context
        self.execution_count += 1

        return AgentResult(
            success=True,
            output={
                "message": "agent executed",
            },
        )


class InspectableResearchAgent(ResearchAgent):
    """
    ResearchAgent used to inspect the AgentExecutionContext
    created by AgentRuntime.
    """

    def __init__(self, identity: AgentIdentity):
        super().__init__(identity)
        self.execution_context: AgentExecutionContext | None = None

    async def run(
        self,
        task,
        agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:

        self.execution_context = agent_execution_context

        return await super().run(
            task,
            agent_execution_context,
        )


def create_runtime_context() -> RuntimeContext:
    """
    Create a RuntimeContext using ExecutionRuntime,
    matching the production construction path.
    """

    trace_recorder = TraceRecorder()
    execution_runtime = ExecutionRuntime(trace_recorder)

    return execution_runtime.create_context()


def create_agent(
    agent_id: str = "mock-agent",
) -> MockAgent:
    return MockAgent(
        identity=AgentIdentity(
            agent_id=agent_id,
            agent_type="test",
            name="MockAgent",
        )
    )


def create_agent_checkpoint(
    agent_id: str,
) -> AgentCheckpoint:
    return AgentCheckpoint(
        agent_id=agent_id,
        status="RUNNING",
        state=ContextState(),
        loop=LoopState(
            step_count=7,
            reflection_count=2,
        ),
    )


@pytest.mark.asyncio
async def test_agent_runtime_execute():
    """
    Normal AgentRuntime execution still works.
    """

    agent = create_agent()

    runtime = AgentRuntime()

    context = create_runtime_context()

    task = TaskRequest(
        task_id="1",
        user_input="test",
    )

    result = await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=context,
    )

    assert isinstance(
        result,
        AgentResult,
    )

    assert result.success is True

    assert result.output["message"] == "agent executed"

    assert agent.execution_count == 1


@pytest.mark.asyncio
async def test_agent_runtime_creates_agent_execution_context():
    """
    Normal execution creates a new AgentExecutionContext.
    """

    agent = create_agent()

    runtime = AgentRuntime()

    context = create_runtime_context()

    task = TaskRequest(
        task_id="task-001",
        user_input="test",
    )

    await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=context,
    )

    assert agent.execution_context is not None

    execution_context = agent.execution_context

    assert execution_context.runtime_context is context

    assert execution_context.agent_identity is agent.identity

    assert execution_context.agent_context is agent.context

    assert execution_context.memory is agent.memory

    assert isinstance(
        execution_context.state,
        ContextState,
    )

    assert isinstance(
        execution_context.loop,
        LoopState,
    )


@pytest.mark.asyncio
async def test_agent_execution_context_state_is_isolated_per_invocation():
    """
    Each normal Agent invocation gets a new execution-local state.
    """

    agent = create_agent()

    runtime = AgentRuntime()

    context = create_runtime_context()

    task = TaskRequest(
        task_id="task-002",
        user_input="test",
    )

    await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=context,
    )

    first_context = agent.execution_context

    assert first_context is not None

    first_state = first_context.state
    first_loop = first_context.loop

    await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=context,
    )

    second_context = agent.execution_context

    assert second_context is not None

    assert first_state is not second_context.state
    assert first_loop is not second_context.loop


@pytest.mark.asyncio
async def test_agent_runtime_reuses_supplied_execution_context():
    """
    If an AgentExecutionContext is supplied, AgentRuntime must
    reuse it instead of creating another one.
    """

    agent = create_agent()

    runtime = AgentRuntime()

    context = create_runtime_context()

    task = TaskRequest(
        task_id="task-003",
        user_input="test",
    )

    execution_context = AgentExecutionContext.create(
        runtime_context=context,
        agent=agent,
    )

    execution_context.loop.step_count = 42
    execution_context.loop.reflection_count = 3

    result = await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=context,
        agent_execution_context=execution_context,
    )

    assert result.success is True

    assert agent.execution_context is execution_context

    assert agent.execution_context.loop.step_count == 42

    assert agent.execution_context.loop.reflection_count == 3


@pytest.mark.asyncio
async def test_agent_runtime_rejects_execution_context_from_different_agent():
    """
    A context belonging to another Agent must not be reused.
    """

    first_agent = create_agent(
        agent_id="agent-001",
    )

    second_agent = create_agent(
        agent_id="agent-002",
    )

    runtime = AgentRuntime()

    context = create_runtime_context()

    task = TaskRequest(
        task_id="task-004",
        user_input="test",
    )

    execution_context = AgentExecutionContext.create(
        runtime_context=context,
        agent=first_agent,
    )

    with pytest.raises(
        ValueError,
        match="different Agent",
    ):
        await runtime.execute(
            agent=second_agent,
            task=task,
            runtime_context=context,
            agent_execution_context=execution_context,
        )


@pytest.mark.asyncio
async def test_agent_runtime_rejects_execution_context_from_different_runtime():
    """
    A context belonging to another Runtime execution must not
    be reused.
    """

    agent = create_agent()

    runtime = AgentRuntime()

    first_runtime_context = create_runtime_context()
    second_runtime_context = create_runtime_context()

    task = TaskRequest(
        task_id="task-005",
        user_input="test",
    )

    execution_context = AgentExecutionContext.create(
        runtime_context=first_runtime_context,
        agent=agent,
    )

    with pytest.raises(
        ValueError,
        match="different RuntimeContext",
    ):
        await runtime.execute(
            agent=agent,
            task=task,
            runtime_context=second_runtime_context,
            agent_execution_context=execution_context,
        )


def test_restore_execution_context_restores_checkpoint_state():
    """
    AgentRuntime restores execution-local state from
    AgentCheckpoint.
    """

    agent = create_agent()

    runtime = AgentRuntime()

    runtime_context = create_runtime_context()

    checkpoint = create_agent_checkpoint(
        agent_id=agent.identity.agent_id,
    )

    execution_context = runtime._restore_execution_context(
        runtime_context=runtime_context,
        agent=agent,
        checkpoint=checkpoint,
    )

    assert execution_context.runtime_context is runtime_context

    assert execution_context.agent_identity is agent.identity

    assert execution_context.state == checkpoint.state

    assert execution_context.loop == checkpoint.loop

    assert execution_context.loop.step_count == 7

    assert execution_context.loop.reflection_count == 2


def test_restore_execution_context_preserves_agent_context():
    """
    Recovery must continue using the existing AgentContext
    owned by the live Agent instance.
    """

    agent = create_agent()

    runtime = AgentRuntime()

    runtime_context = create_runtime_context()

    checkpoint = create_agent_checkpoint(
        agent_id=agent.identity.agent_id,
    )

    execution_context = runtime._restore_execution_context(
        runtime_context=runtime_context,
        agent=agent,
        checkpoint=checkpoint,
    )

    assert execution_context.agent_context is agent.context


def test_restore_execution_context_preserves_memory_runtime():
    """
    Recovery must continue using the MemoryRuntime owned by
    the live Agent instance.
    """

    agent = create_agent()

    runtime = AgentRuntime()

    runtime_context = create_runtime_context()

    checkpoint = create_agent_checkpoint(
        agent_id=agent.identity.agent_id,
    )

    execution_context = runtime._restore_execution_context(
        runtime_context=runtime_context,
        agent=agent,
        checkpoint=checkpoint,
    )

    assert execution_context.memory is agent.memory


def test_restore_execution_context_uses_current_agent_identity():
    """
    AgentIdentity is not restored from the checkpoint.

    The live Agent remains the source of AgentIdentity.
    """

    agent = create_agent()

    runtime = AgentRuntime()

    runtime_context = create_runtime_context()

    checkpoint = create_agent_checkpoint(
        agent_id=agent.identity.agent_id,
    )

    execution_context = runtime._restore_execution_context(
        runtime_context=runtime_context,
        agent=agent,
        checkpoint=checkpoint,
    )

    assert execution_context.agent_identity is agent.identity


def test_restore_execution_context_rejects_agent_identity_mismatch():
    """
    A checkpoint belonging to another Agent must be rejected.
    """

    agent = create_agent(
        agent_id="research-agent",
    )

    runtime = AgentRuntime()

    runtime_context = create_runtime_context()

    checkpoint = create_agent_checkpoint(
        agent_id="risk-agent",
    )

    with pytest.raises(
        ValueError,
        match="Agent checkpoint identity mismatch",
    ):
        runtime._restore_execution_context(
            runtime_context=runtime_context,
            agent=agent,
            checkpoint=checkpoint,
        )


@pytest.mark.asyncio
async def test_restored_execution_context_can_be_passed_to_agent_runtime():
    """
    A context restored from checkpoint can be supplied to
    AgentRuntime and eventually reaches Agent.execute().
    """

    agent = create_agent()

    runtime = AgentRuntime()

    runtime_context = create_runtime_context()

    checkpoint = create_agent_checkpoint(
        agent_id=agent.identity.agent_id,
    )

    restored_context = runtime._restore_execution_context(
        runtime_context=runtime_context,
        agent=agent,
        checkpoint=checkpoint,
    )

    task = TaskRequest(
        task_id="task-recovery-001",
        user_input="continue",
    )

    result = await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=runtime_context,
        agent_execution_context=restored_context,
    )

    assert result.success is True

    assert agent.execution_count == 1

    assert agent.execution_context is restored_context

    assert agent.execution_context.loop.step_count == 7

    assert agent.execution_context.loop.reflection_count == 2


@pytest.mark.asyncio
async def test_restored_execution_context_reaches_agent_execute():
    """
    Recovery must not bypass the normal Agent execution entry.
    """

    agent = create_agent()

    runtime = AgentRuntime()

    runtime_context = create_runtime_context()

    checkpoint = create_agent_checkpoint(
        agent_id=agent.identity.agent_id,
    )

    restored_context = runtime._restore_execution_context(
        runtime_context=runtime_context,
        agent=agent,
        checkpoint=checkpoint,
    )

    task = TaskRequest(
        task_id="task-recovery-002",
        user_input="continue",
    )

    await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=runtime_context,
        agent_execution_context=restored_context,
    )

    assert agent.execution_context is restored_context

    assert agent.execution_count == 1


@pytest.mark.asyncio
async def test_multiple_agents_can_share_runtime_context_but_have_independent_execution_contexts():
    """
    Multiple Agent invocations may share one RuntimeContext,
    while each invocation owns independent execution-local state.
    """

    first_agent = create_agent(
        agent_id="agent-001",
    )

    second_agent = create_agent(
        agent_id="agent-002",
    )

    runtime = AgentRuntime()

    runtime_context = create_runtime_context()

    task = TaskRequest(
        task_id="task-006",
        user_input="test",
    )

    await runtime.execute(
        agent=first_agent,
        task=task,
        runtime_context=runtime_context,
    )

    await runtime.execute(
        agent=second_agent,
        task=task,
        runtime_context=runtime_context,
    )

    first_context = first_agent.execution_context
    second_context = second_agent.execution_context

    assert first_context is not None
    assert second_context is not None

    # Same Execution.
    assert first_context.runtime_context is runtime_context
    assert second_context.runtime_context is runtime_context

    # Different Agent instances.
    assert first_context.agent_identity is first_agent.identity
    assert second_context.agent_identity is second_agent.identity

    # Independent invocation-local state.
    assert first_context.state is not second_context.state
    assert first_context.loop is not second_context.loop

    first_context.loop.step_count = 100

    assert first_context.loop.step_count == 100
    assert second_context.loop.step_count == 0