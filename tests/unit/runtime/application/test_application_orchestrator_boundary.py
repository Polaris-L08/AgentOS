from unittest.mock import AsyncMock, Mock

import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.agents.agent_registry import AgentRegistry
from runtime.execution import Execution
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.orchestration import (
    OrchestrationResult,
    SingleAgentOrchestrator,
)
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    async def run(
        self,
        task,
        agent_execution_context,
    ):
        return AgentResult(
            success=True,
            output=f"processed: {task.user_input}",
        )


def create_agent() -> MockAgent:
    return MockAgent(
        identity=AgentIdentity(
            agent_id="agent-1",
            agent_type="mock",
            name="Mock Agent",
        )
    )


def create_orchestrator():
    agent = create_agent()

    registry = AgentRegistry(
        agents=[agent]
    )

    agent_runtime = AgentRuntime()

    orchestrator = SingleAgentOrchestrator(
        agent_registry=registry,
        agent_runtime=agent_runtime,
    )

    return orchestrator, agent, agent_runtime


def test_orchestrator_does_not_depend_on_application():
    orchestrator, _, _ = create_orchestrator()

    assert not hasattr(
        orchestrator,
        "_application",
    )


@pytest.mark.asyncio
async def test_orchestrator_executes_agent_directly_through_agent_runtime():
    orchestrator, agent, agent_runtime = create_orchestrator()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    execution = Execution(
        execution_id="execution-1",
        task_id=task.task_id,
    )

    execution_handle = execution_runtime.create_execution(execution)

    original_execute = agent_runtime.execute

    calls = []

    async def recording_execute(
        *,
        agent,
        task,
        runtime_context,
        agent_execution_context=None,
    ):
        calls.append(
            {
                "agent": agent,
                "task": task,
                "runtime_context": runtime_context,
            }
        )

        return await original_execute(
            agent=agent,
            task=task,
            runtime_context=runtime_context,
            agent_execution_context=agent_execution_context,
        )

    orchestrator._agent_runtime.execute = recording_execute

    result = await orchestrator.execute(
        task=task,
        execution_handle=execution_handle,
    )

    assert isinstance(
        result,
        OrchestrationResult,
    )

    assert result.agent is agent
    assert result.agent_result.success is True
    assert result.agent_result.output == "processed: hello"

    assert len(calls) == 1
    assert calls[0]["agent"] is agent
    assert calls[0]["task"] is task
    assert (
        calls[0]["runtime_context"]
        is execution_handle.runtime_context
    )

    await execution_handle.close()


def test_orchestrator_has_no_application_dependency():
    orchestrator, _, _ = create_orchestrator()

    assert not hasattr(
        orchestrator,
        "application",
    )