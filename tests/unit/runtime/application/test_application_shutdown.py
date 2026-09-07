from __future__ import annotations

import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from runtime.application.application import AgentApplication
from runtime.application.application_assembly import ApplicationAssembly
from runtime.application.application_config import ApplicationConfig
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
    ApplicationState,
)
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    async def run(self, task, agent_execution_context):
        return f"completed: {task.user_input}"


def create_agent(agent_id: str = "agent-1") -> BaseAgent:
    return MockAgent(
        identity=AgentIdentity(
            agent_id=agent_id,
            agent_type="mock",
            name=agent_id,
        )
    )


def create_application(
    agents: list[BaseAgent] | None = None,
) -> AgentApplication:
    agent_runtime = AgentRuntime()
    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    assembly = (
        ApplicationAssembly(
            ApplicationConfig(
                application_id="test-app",
                name="Test Application",
            )
        )
        .register_component("agent_runtime", agent_runtime)
        .register_component("execution_runtime", execution_runtime)
    )

    for agent in agents or []:
        assembly.add_agent(agent)

    return assembly.build()


@pytest.mark.asyncio
async def test_application_stop_transitions_to_stopped():
    application = create_application([create_agent()])

    await application.initialize()
    await application.start()

    assert application.state is ApplicationState.RUNNING

    await application.stop()

    assert application.state is ApplicationState.STOPPED
    assert application.is_running is False


@pytest.mark.asyncio
async def test_application_stop_is_not_allowed_before_start():
    application = create_application([create_agent()])

    await application.initialize()

    with pytest.raises(ApplicationLifecycleError):
        await application.stop()


@pytest.mark.asyncio
async def test_application_cannot_restart_after_stop():
    application = create_application([create_agent()])

    await application.initialize()
    await application.start()
    await application.stop()

    with pytest.raises(ApplicationLifecycleError):
        await application.start()


@pytest.mark.asyncio
async def test_application_shutdown_failure_keeps_stopping_state():
    application = create_application([create_agent()])

    await application.initialize()
    await application.start()

    async def failing_shutdown():
        raise RuntimeError("shutdown failure")

    application._shutdown_components = failing_shutdown

    with pytest.raises(RuntimeError, match="shutdown failure"):
        await application.stop()

    assert application.state is ApplicationState.STOPPING
    assert application.is_running is False