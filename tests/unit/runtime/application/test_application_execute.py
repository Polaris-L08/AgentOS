from __future__ import annotations

import asyncio

import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from models.task_result import TaskResult
from runtime.application.application import AgentApplication
from runtime.application.application_assembly import ApplicationAssembly
from runtime.application.application_config import ApplicationConfig
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.events.event_bus import EventBus
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    async def run(self, task, agent_execution_context):
        return f"completed: {task.user_input}"


class FailingAgent(BaseAgent):
    async def run(self, task, agent_execution_context):
        raise RuntimeError("agent failure")


class BlockingAgent(BaseAgent):
    async def run(self, task, agent_execution_context):
        await asyncio.Event().wait()


def create_agent(
    agent_id: str,
    agent_type: str = "mock",
) -> BaseAgent:
    return MockAgent(
        identity=AgentIdentity(
            agent_id=agent_id,
            agent_type=agent_type,
            name=agent_id,
        )
    )


def create_application(
    agents: list[BaseAgent],
) -> AgentApplication:
    event_bus = EventBus()

    agent_runtime = AgentRuntime(
        publisher=event_bus,
    )

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    assembly = (
        ApplicationAssembly(
            ApplicationConfig(
                application_id="test-app",
                name="Test Application",
            )
        )
        .register_component(
            "agent_runtime",
            agent_runtime,
        )
        .register_component(
            "execution_runtime",
            execution_runtime,
        )
        .register_component(
            "publisher",
            event_bus,
        )
    )

    for agent in agents:
        assembly.add_agent(agent)

    return assembly.build()


@pytest.mark.asyncio
async def test_application_execute_runs_single_agent():
    agent = create_agent("agent-1")

    application = create_application([agent])

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    result = await application.execute(task)

    assert result.success is True
    assert result.answer == "completed: hello"

    await application.stop()


@pytest.mark.asyncio
async def test_application_execute_requires_running_application():
    agent = create_agent("agent-1")

    application = create_application([agent])

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    with pytest.raises(ApplicationLifecycleError):
        await application.execute(task)


@pytest.mark.asyncio
async def test_application_execute_fails_when_no_agent_exists():
    application = create_application([])

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    with pytest.raises(ApplicationLifecycleError):
        await application.execute(task)

    await application.stop()


@pytest.mark.asyncio
async def test_application_execute_fails_when_multiple_agents_exist():
    agent1 = create_agent("agent-1")
    agent2 = create_agent("agent-2")

    application = create_application(
        [
            agent1,
            agent2,
        ]
    )

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    with pytest.raises(ApplicationLifecycleError):
        await application.execute(task)

    await application.stop()


@pytest.mark.asyncio
async def test_application_execute_propagates_agent_failure():
    failing_agent = FailingAgent(
        identity=AgentIdentity(
            agent_id="failing-agent",
            agent_type="failing",
            name="Failing Agent",
        )
    )

    application = create_application([failing_agent])

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    with pytest.raises(
        RuntimeError,
        match="agent failure",
    ):
        await application.execute(task)

    await application.stop()


@pytest.mark.asyncio
async def test_application_execute_propagates_cancellation():
    blocking_agent = BlockingAgent(
        identity=AgentIdentity(
            agent_id="blocking-agent",
            agent_type="blocking",
            name="Blocking Agent",
        )
    )

    application = create_application([blocking_agent])

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    execution_task = asyncio.create_task(
        application.execute(task)
    )

    await asyncio.sleep(0)

    execution_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await execution_task

    await application.stop()


@pytest.mark.asyncio
async def test_application_execute_can_be_called_multiple_times():
    agent = create_agent("agent-1")

    application = create_application([agent])

    await application.initialize()
    await application.start()

    task1 = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    task2 = TaskRequest(
        task_id="task-2",
        user_input="world",
    )

    result1 = await application.execute(task1)
    result2 = await application.execute(task2)

    assert result1.success is True
    assert result1.answer == "completed: hello"

    assert result2.success is True
    assert result2.answer == "completed: world"

    await application.stop()


@pytest.mark.asyncio
async def test_application_execute_returns_task_result():
    agent = create_agent("agent-1")

    application = create_application([agent])

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    result = await application.execute(task)

    assert isinstance(result, TaskResult)

    assert result.success is True
    assert result.answer == "completed: hello"

    assert result.metadata["task_id"] == "task-1"
    assert result.metadata["agent_id"] == "agent-1"
    assert result.metadata["agent_type"] == "mock"

    await application.stop()