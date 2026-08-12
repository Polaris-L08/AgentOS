from __future__ import annotations

import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from agents.research.research_agent import ResearchAgent
from models.task_request import TaskRequest
from runtime.context import AgentExecutionContext
from runtime.context.runtime_context import RuntimeContext
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    """
    Simple Agent used for AgentRuntime testing.
    """

    async def run(
            self,
            task,
            agent_execution_context: AgentExecutionContext
    ):

        return AgentResult(
            success=True,
            output={
                "message": "agent executed"
            }
        )

class InspectableResearchAgent(ResearchAgent):
    """
    ResearchAgent used to inspect the AgentExecutionContext
    created by AgentRuntime.

    The actual research logic is inherited from ResearchAgent.
    This subclass only records the execution context so that
    the test can verify Runtime isolation semantics.
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
    Create RuntimeContext for test.

    This should follow the same construction
    pattern used by ExecutionRuntime.
    """
    trace_recorder = TraceRecorder()
    execution_runtime = ExecutionRuntime(trace_recorder)
    execution_context = execution_runtime.create_context()

    return execution_context


@pytest.mark.asyncio
async def test_agent_runtime_execute():

    agent = MockAgent(
        identity=AgentIdentity(
            agent_id="mock-agent",
            agent_type="test",
            name="MockAgent"
        )
    )


    runtime = AgentRuntime()


    context = create_runtime_context()

    task = TaskRequest(task_id="1", user_input="test")

    result = await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=context
    )


    assert isinstance(
        result,
        AgentResult
    )

    assert result.success is True

    assert result.output["message"] == "agent executed"

@pytest.mark.asyncio
async def test_agent_runtime_execute_research_agent():

    agent = ResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent",
            agent_type="investment_research",
            name="ResearchAgent",
        )
    )

    runtime = AgentRuntime()

    context = create_runtime_context()

    task = TaskRequest(
        task_id="research-task-001",
        user_input="Analyze NVIDIA stock",
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

    assert result.output["agent"] == "ResearchAgent"

    assert (
        result.output["task_id"]
        == "research-task-001"
    )

    assert (
        result.output["research_request"]
        == "Analyze NVIDIA stock"
    )

    assert (
        result.output["analysis"]
        == "Research task accepted: "
           "Analyze NVIDIA stock"
    )

@pytest.mark.asyncio
async def test_agent_runtime_creates_isolated_agent_execution_context():

    agent = InspectableResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent",
            agent_type="investment_research",
            name="ResearchAgent",
        )
    )

    runtime = AgentRuntime()

    context = create_runtime_context()

    task = TaskRequest(
        task_id="research-task-002",
        user_input="Analyze NVIDIA stock",
    )

    result = await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=context,
    )

    assert result.success is True

    assert agent.execution_context is not None

    agent_context = agent.execution_context

    # ---------------------------------------------------------
    # 1. AgentExecutionContext belongs to this RuntimeContext.
    # ---------------------------------------------------------

    assert (
        agent_context.runtime_context
        is context
    )

    # ---------------------------------------------------------
    # 2. Agent has its own AgentIdentity.
    # ---------------------------------------------------------

    assert (
        agent_context.agent_identity
        is agent.identity
    )

    # ---------------------------------------------------------
    # 3. Agent owns an isolated ContextState.
    #
    # AgentExecutionContext.create() must not directly reuse
    # RuntimeContext.state.
    # ---------------------------------------------------------

    assert (
        agent_context.state
        is not context.state
    )

    # ---------------------------------------------------------
    # 4. Agent owns an isolated LoopState.
    #
    # A child Agent must not modify the execution loop of
    # the caller.
    # ---------------------------------------------------------

    assert (
        agent_context.loop
        is not context.loop
    )

@pytest.mark.asyncio
async def test_agent_execution_context_state_is_isolated():

    agent = InspectableResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent",
            agent_type="investment_research",
            name="ResearchAgent",
        )
    )

    runtime = AgentRuntime()

    context = create_runtime_context()

    task = TaskRequest(
        task_id="research-task-003",
        user_input="Analyze NVIDIA stock",
    )

    await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=context,
    )

    assert agent.execution_context is not None

    agent_context = agent.execution_context

    # Modify Agent private execution state.
    agent_context.loop.step_count = 10

    # The RuntimeContext loop must remain untouched.
    assert context.loop.step_count == 0

@pytest.mark.asyncio
async def test_multiple_agent_invocations_have_isolated_execution_contexts():

    first_agent = InspectableResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-001",
            agent_type="investment_research",
            name="ResearchAgent-1",
        )
    )

    second_agent = InspectableResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-002",
            agent_type="investment_research",
            name="ResearchAgent-2",
        )
    )

    runtime = AgentRuntime()

    context = create_runtime_context()

    task = TaskRequest(
        task_id="research-task-004",
        user_input="Analyze NVIDIA stock",
    )

    await runtime.execute(
        agent=first_agent,
        task=task,
        runtime_context=context,
    )

    await runtime.execute(
        agent=second_agent,
        task=task,
        runtime_context=context,
    )

    assert first_agent.execution_context is not None
    assert second_agent.execution_context is not None

    first_context = first_agent.execution_context
    second_context = second_agent.execution_context

    # Both executions belong to the same RuntimeContext.
    assert (
        first_context.runtime_context
        is context
    )

    assert (
        second_context.runtime_context
        is context
    )

    # But each Agent invocation owns independent state.
    assert (
        first_context.state
        is not second_context.state
    )

    assert (
        first_context.loop
        is not second_context.loop
    )

    # Modifying Agent A must not affect Agent B.
    first_context.loop.step_count = 100

    assert first_context.loop.step_count == 100
    assert second_context.loop.step_count == 0