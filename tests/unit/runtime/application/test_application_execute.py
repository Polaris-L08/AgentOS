from __future__ import annotations

import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
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
        import asyncio

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

    return (
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
        .add_agent(
            agents[0],
        )
        .build()
    )


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
    assert result.output == "completed: hello"

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
    event_bus = EventBus()

    agent_runtime = AgentRuntime(
        publisher=event_bus,
    )

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    application = (
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
        .build()
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
async def test_application_execute_fails_when_multiple_agents_exist():
    event_bus = EventBus()

    agent_runtime = AgentRuntime(
        publisher=event_bus,
    )

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    agent1 = create_agent("agent-1")
    agent2 = create_agent("agent-2")

    application = (
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
        .add_agent(agent1)
        .add_agent(agent2)
        .build()
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
async def test_application_execute_closes_execution_after_success():
    agent = create_agent("agent-1")

    application = create_application([agent])

    execution_runtime = application.execution_runtime

    created_handles = []

    original_create_execution = (
        execution_runtime.create_execution
    )

    def create_execution():
        handle = original_create_execution()
        created_handles.append(handle)
        return handle

    execution_runtime.create_execution = create_execution

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    await application.execute(task)

    assert len(created_handles) == 1
    assert created_handles[0].closed is True

    await application.stop()


@pytest.mark.asyncio
async def test_application_execute_closes_execution_after_agent_failure():
    event_bus = EventBus()

    agent_runtime = AgentRuntime(
        publisher=event_bus,
    )

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    failing_agent = FailingAgent(
        identity=AgentIdentity(
            agent_id="failing-agent",
            agent_type="failing",
            name="Failing Agent",
        )
    )

    application = (
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
        .add_agent(
            failing_agent,
        )
        .build()
    )

    created_handles = []

    original_create_execution = (
        execution_runtime.create_execution
    )

    def create_execution():
        handle = original_create_execution()
        created_handles.append(handle)
        return handle

    execution_runtime.create_execution = create_execution

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    with pytest.raises(RuntimeError, match="agent failure"):
        await application.execute(task)

    assert len(created_handles) == 1
    assert created_handles[0].closed is True

    await application.stop()


# ----------------------------------------
# Cancellation Test
# ----------------------------------------

@pytest.mark.asyncio
async def test_application_execute_closes_execution_on_cancellation():
    import asyncio

    event_bus = EventBus()

    agent_runtime = AgentRuntime(
        publisher=event_bus,
    )

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    blocking_agent = BlockingAgent(
        identity=AgentIdentity(
            agent_id="blocking-agent",
            agent_type="blocking",
            name="Blocking Agent",
        )
    )

    application = (
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
        .add_agent(
            blocking_agent,
        )
        .build()
    )

    created_handles = []

    original_create_execution = (
        execution_runtime.create_execution
    )

    def create_execution():
        handle = original_create_execution()
        created_handles.append(handle)
        return handle

    # execution_runtime.create_execution = create_execution

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

    assert len(created_handles) == 1
    assert created_handles[0].closed is True

    await application.stop()