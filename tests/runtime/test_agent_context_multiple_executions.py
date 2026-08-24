import pytest

from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.context import AgentExecutionContext
from runtime.context.memory_item import MemoryItem
from runtime.execution import AgentRuntime
from tests.runtime.test_agent_runtime import MockAgent, create_runtime_context


@pytest.mark.asyncio
async def test_agent_context_survives_multiple_executions():

    agent = MockAgent(
        identity=AgentIdentity(
            agent_id="memory-agent",
            agent_type="test",
            name="MemoryAgent",
        )
    )

    runtime = AgentRuntime()

    runtime_context_1 = create_runtime_context()

    task_1 = TaskRequest(
        task_id="task-001",
        user_input="first execution",
    )

    execution_context_1 = AgentExecutionContext.create(
        runtime_context_1,
        agent,
    )

    agent_context = execution_context_1.agent_context

    agent_context.memory_state.items.append(
        MemoryItem(
            content="NVIDIA research completed",
        )
    )

    await runtime.execute(
        agent=agent,
        task=task_1,
        runtime_context=runtime_context_1,
        agent_execution_context=execution_context_1,
    )

    # ---------------------------------------------------------
    # A new Runtime execution
    # ---------------------------------------------------------

    runtime_context_2 = create_runtime_context()

    task_2 = TaskRequest(
        task_id="task-002",
        user_input="second execution",
    )

    execution_context_2 = AgentExecutionContext.create(
        runtime_context_2,
        agent,
    )

    # ---------------------------------------------------------
    # AgentContext survives.
    # ---------------------------------------------------------

    assert (
        execution_context_2.agent_context
        is agent.context
    )

    assert (
        execution_context_1.agent_context
        is execution_context_2.agent_context
    )

    assert (
        execution_context_2.agent_context
        is not execution_context_2.state
    )

    assert (
        execution_context_2.agent_context
        .memory_state
        .items[0]
        .content
        == "NVIDIA research completed"
    )

    # ---------------------------------------------------------
    # Execution contexts are different.
    # ---------------------------------------------------------

    assert execution_context_1 is not execution_context_2

    assert execution_context_1.loop is not execution_context_2.loop

    assert execution_context_1.state is not execution_context_2.state

    # ---------------------------------------------------------
    # Runtime contexts are also different.
    # ---------------------------------------------------------

    assert runtime_context_1 is not runtime_context_2

# 两个 Agent 之间不能共享 AgentContext
def test_agents_have_isolated_agent_context():

    agent_a = MockAgent(
        identity=AgentIdentity(
            agent_id="agent-a",
            agent_type="test",
            name="AgentA",
        )
    )

    agent_b = MockAgent(
        identity=AgentIdentity(
            agent_id="agent-b",
            agent_type="test",
            name="AgentB",
        )
    )

    assert agent_a.context is not agent_b.context

    agent_a.context.memory_state.items.append(
        MemoryItem(
            content="private memory",
        )
    )

    assert (
        len(agent_b.context.memory_state.items)
        == 0
    )

# 同一个 Agent 的不同 Invocation，不应该共享 LoopState。
def test_agent_execution_context_is_isolated():

    agent = MockAgent(
        identity=AgentIdentity(
            agent_id="agent-a",
            agent_type="test",
            name="AgentA",
        )
    )

    runtime_context = create_runtime_context()

    execution_1 = AgentExecutionContext.create(
        runtime_context,
        agent,
    )

    execution_2 = AgentExecutionContext.create(
        runtime_context,
        agent,
    )

    execution_1.loop.step_count = 10

    assert execution_2.loop.step_count == 0

    assert execution_1.loop is not execution_2.loop

    # But AgentContext remains shared by this Agent.
    assert (
        execution_1.agent_context
        is execution_2.agent_context
    )