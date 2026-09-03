from __future__ import annotations

import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.context import AgentExecutionContext
from runtime.context.memory_item import MemorySource
from runtime.context.runtime_context import RuntimeContext
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class MemoryUsingAgent(BaseAgent):
    """Agent that accesses Memory exclusively through its execution context."""

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:
        await agent_execution_context.memory.remember(
            content=task.user_input,
            runtime_context=agent_execution_context.runtime_context,
            source=MemorySource.HISTORY,
        )

        memories = await agent_execution_context.memory.query(
            query=task.user_input,
            runtime_context=agent_execution_context.runtime_context,
            limit=1,
        )

        return AgentResult(
            success=True,
            output={
                "memory_count": len(memories),
                "memory_content": memories[0].content if memories else None,
            },
        )


def create_runtime_context() -> RuntimeContext:
    recorder = TraceRecorder()
    execution_runtime = ExecutionRuntime(recorder)
    return execution_runtime.create_context()


@pytest.mark.asyncio
async def test_agent_execution_context_exposes_agent_memory_runtime(runtime_context):
    agent = MemoryUsingAgent(
        identity=AgentIdentity(
            agent_id="memory-context-agent",
            agent_type="test",
            name="MemoryContextAgent",
        )
    )

    runtime = AgentRuntime()
    # runtime_context = create_runtime_context()

    execution_context = AgentExecutionContext.create(
        runtime_context=runtime_context,
        agent=agent,
    )

    assert execution_context.memory is agent.memory
    assert execution_context.agent_context is agent.context
    assert execution_context.runtime_context is runtime_context


@pytest.mark.asyncio
async def test_memory_participates_in_real_agent_execution(runtime_context):
    agent = MemoryUsingAgent(
        identity=AgentIdentity(
            agent_id="memory-execution-agent",
            agent_type="test",
            name="MemoryExecutionAgent",
        )
    )

    runtime = AgentRuntime()
    # runtime_context = create_runtime_context()

    result = await runtime.execute(
        agent=agent,
        task=TaskRequest(
            task_id="memory-execution-task",
            user_input="remember this execution fact",
        ),
        runtime_context=runtime_context,
    )

    assert result.success is True
    assert result.output["memory_count"] == 1
    assert result.output["memory_content"] == "remember this execution fact"


@pytest.mark.asyncio
async def test_multiple_executions_share_agent_memory_but_not_execution_context():
    agent = MemoryUsingAgent(
        identity=AgentIdentity(
            agent_id="memory-lifetime-agent",
            agent_type="test",
            name="MemoryLifetimeAgent",
        )
    )

    runtime = AgentRuntime()
    runtime_context_1 = create_runtime_context()
    runtime_context_2 = create_runtime_context()

    execution_context_1 = AgentExecutionContext.create(
        runtime_context=runtime_context_1,
        agent=agent,
    )
    execution_context_2 = AgentExecutionContext.create(
        runtime_context=runtime_context_2,
        agent=agent,
    )

    assert execution_context_1 is not execution_context_2
    assert execution_context_1.memory is execution_context_2.memory
    assert execution_context_1.memory is agent.memory
    assert execution_context_1.runtime_context is not execution_context_2.runtime_context


@pytest.mark.asyncio
async def test_different_agents_do_not_share_memory_runtime(runtime_context):
    agent_a = MemoryUsingAgent(
        identity=AgentIdentity(
            agent_id="memory-agent-a",
            agent_type="test",
            name="MemoryAgentA",
        )
    )
    agent_b = MemoryUsingAgent(
        identity=AgentIdentity(
            agent_id="memory-agent-b",
            agent_type="test",
            name="MemoryAgentB",
        )
    )

    # runtime_context = create_runtime_context()

    execution_a = AgentExecutionContext.create(runtime_context, agent_a)
    execution_b = AgentExecutionContext.create(runtime_context, agent_b)

    assert execution_a.memory is agent_a.memory
    assert execution_b.memory is agent_b.memory
    assert execution_a.memory is not execution_b.memory
