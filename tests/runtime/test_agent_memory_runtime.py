import pytest

from agents import BaseAgent, AgentResult, identity
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.context import AgentExecutionContext
from runtime.context.memory_item import MemoryItem
from runtime.execution import AgentRuntime
from runtime.memory import InMemoryMemoryStore
from tests.runtime.test_agent_runtime import create_runtime_context

class MockMemoryAgent(BaseAgent):
    async def run(
            self,
            task,
            agent_execution_context: AgentExecutionContext
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output=f"${self.identity.name} executed successfully",
        )

@pytest.mark.asyncio
async def test_memory_survives_multiple_executions():

    agent = MockMemoryAgent(
        identity=AgentIdentity(
            agent_id="memory-agent",
            agent_type="test",
            name="MemoryAgent",
        )
    )

    runtime = AgentRuntime()

    context_1 = create_runtime_context()

    execution_1 = AgentExecutionContext.create(
        context_1,
        agent,
    )

    await agent.memory.write(
        MemoryItem(
            content="NVIDIA research completed"
        ),
        context_1,
    )

    await runtime.execute(
        agent=agent,
        task=TaskRequest(
            task_id="task-001",
            user_input="first",
        ),
        runtime_context=context_1,
        agent_execution_context=execution_1,
    )

    # A completely new Runtime Execution.
    context_2 = create_runtime_context()

    execution_2 = AgentExecutionContext.create(
        context_2,
        agent,
    )

    memories = await agent.memory.read(
        context_2
    )

    assert len(memories) == 1

    assert (
        memories[0].content
        == "NVIDIA research completed"
    )

    # AgentContext survives.
    assert (
        execution_1.agent_context
        is execution_2.agent_context
    )

    # Execution contexts do not.
    assert execution_1 is not execution_2

    assert execution_1.loop is not execution_2.loop

@pytest.mark.asyncio
async def test_memory_isolated_between_agents():

    store = InMemoryMemoryStore()

    agent_a = MockMemoryAgent(
        identity=AgentIdentity(
            agent_id="agent-a",
            agent_type="test",
            name="AgentA",
        ),
        memory_store=store,
    )

    agent_b = MockMemoryAgent(
        identity=AgentIdentity(
            agent_id="agent-b",
            agent_type="test",
            name="AgentB",
        ),
        memory_store=store,
    )

    context = create_runtime_context()

    await agent_a.memory.write(
        MemoryItem(
            content="private research memory"
        ),
        context,
    )

    assert len(
        await agent_a.memory.read(context)
    ) == 1

    assert (
        await agent_b.memory.read(context)
        == []
    )