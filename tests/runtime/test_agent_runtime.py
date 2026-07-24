from __future__ import annotations


import pytest


from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from agents.result import AgentResult
from models.task_request import TaskRequest
from runtime.context import AgentExecutionContext
from runtime.context.agent_context import AgentContext

from runtime.context.runtime_context import RuntimeContext
from runtime.execution.agent_runtime import AgentRuntime

from runtime.context.context_state import ContextState
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