from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from runtime.application.application import AgentApplication
from runtime.application.application_assembly import ApplicationAssembly
from runtime.application.application_config import ApplicationConfig
from runtime.events.event_bus import EventBus
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.session.session_manager import SessionManager
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    async def run(self, task, agent_execution_context):
        return f"completed: {task.user_input}"


def create_agent(
    agent_id: str,
    agent_type: str = "mock",
) -> MockAgent:
    return MockAgent(
        identity=AgentIdentity(
            agent_id=agent_id,
            agent_type=agent_type,
            name=agent_id,
        )
    )


def create_runtime_components():
    event_bus = EventBus()

    agent_runtime = AgentRuntime(
        publisher=event_bus,
    )

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder(),
    )

    return (
        agent_runtime,
        execution_runtime,
        event_bus,
    )


def create_config() -> ApplicationConfig:
    return ApplicationConfig(
        application_id="test-app",
        name="Test Application",
    )


def test_assembly_builds_application_with_required_components():
    agent_runtime, execution_runtime, _ = create_runtime_components()

    application = (
        ApplicationAssembly(create_config())
        .register_component("agent_runtime", agent_runtime)
        .register_component("execution_runtime", execution_runtime)
        .build()
    )

    assert isinstance(application, AgentApplication)
    assert application.application_id == "test-app"
    assert application.name == "Test Application"

    assert application.agent_runtime is agent_runtime
    assert application.execution_runtime is execution_runtime


def test_assembly_preserves_component_identity():
    agent_runtime, execution_runtime, event_bus = create_runtime_components()

    application = (
        ApplicationAssembly(create_config())
        .register_component("agent_runtime", agent_runtime)
        .register_component("execution_runtime", execution_runtime)
        .register_component("publisher", event_bus)
        .build()
    )

    assert application.agent_runtime is agent_runtime
    assert application.execution_runtime is execution_runtime


def test_assembly_injects_optional_publisher():
    agent_runtime, execution_runtime, event_bus = create_runtime_components()

    application = (
        ApplicationAssembly(create_config())
        .register_component("agent_runtime", agent_runtime)
        .register_component("execution_runtime", execution_runtime)
        .register_component("publisher", event_bus)
        .build()
    )

    assert application._publisher is event_bus


def test_assembly_injects_optional_middleware_chain():
    agent_runtime, execution_runtime, _ = create_runtime_components()

    middleware_chain = MiddlewareChain()

    application = (
        ApplicationAssembly(create_config())
        .register_component("agent_runtime", agent_runtime)
        .register_component("execution_runtime", execution_runtime)
        .register_component("middleware_chain", middleware_chain)
        .build()
    )

    assert application._middleware_chain is middleware_chain


def test_assembly_injects_optional_session_manager():
    agent_runtime, execution_runtime, _ = create_runtime_components()

    session_manager = SessionManager()

    application = (
        ApplicationAssembly(create_config())
        .register_component("agent_runtime", agent_runtime)
        .register_component("execution_runtime", execution_runtime)
        .register_component("session_manager", session_manager)
        .build()
    )

    assert application.session_manager is session_manager


def test_assembly_creates_default_session_manager_when_not_registered():
    agent_runtime, execution_runtime, _ = create_runtime_components()

    application = (
        ApplicationAssembly(create_config())
        .register_component("agent_runtime", agent_runtime)
        .register_component("execution_runtime", execution_runtime)
        .build()
    )

    assert isinstance(application.session_manager, SessionManager)


def test_assembly_registers_agents_into_application():
    agent_runtime, execution_runtime, _ = create_runtime_components()

    agent1 = create_agent("agent-1")
    agent2 = create_agent("agent-2")

    application = (
        ApplicationAssembly(create_config())
        .register_component("agent_runtime", agent_runtime)
        .register_component("execution_runtime", execution_runtime)
        .add_agent(agent1)
        .add_agent(agent2)
        .build()
    )

    assert application.get_agent("agent-1") is agent1
    assert application.get_agent("agent-2") is agent2
    assert len(application.agents) == 2


def test_assembly_rejects_duplicate_agent_ids():
    agent_runtime, execution_runtime, _ = create_runtime_components()

    agent1 = create_agent("agent-1")
    agent2 = create_agent("agent-1")

    assembly = (
        ApplicationAssembly(create_config())
        .register_component("agent_runtime", agent_runtime)
        .register_component("execution_runtime", execution_runtime)
        .add_agent(agent1)
    )

    try:
        assembly.add_agent(agent2)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "Agent already registered" in str(error)


def test_assembly_requires_agent_runtime():
    _, execution_runtime, _ = create_runtime_components()

    assembly = (
        ApplicationAssembly(create_config())
        .register_component("execution_runtime", execution_runtime)
    )

    try:
        assembly.build()
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "agent_runtime" in str(error)


def test_assembly_requires_execution_runtime():
    agent_runtime, _, _ = create_runtime_components()

    assembly = (
        ApplicationAssembly(create_config())
        .register_component("agent_runtime", agent_runtime)
    )

    try:
        assembly.build()
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "execution_runtime" in str(error)


def test_assembly_is_independent_between_builds():
    agent_runtime1, execution_runtime1, _ = create_runtime_components()
    agent_runtime2, execution_runtime2, _ = create_runtime_components()

    application1 = (
        ApplicationAssembly(
            ApplicationConfig(
                application_id="app-1",
                name="Application 1",
            )
        )
        .register_component("agent_runtime", agent_runtime1)
        .register_component("execution_runtime", execution_runtime1)
        .add_agent(create_agent("agent-1"))
        .build()
    )

    application2 = (
        ApplicationAssembly(
            ApplicationConfig(
                application_id="app-2",
                name="Application 2",
            )
        )
        .register_component("agent_runtime", agent_runtime2)
        .register_component("execution_runtime", execution_runtime2)
        .add_agent(create_agent("agent-2"))
        .build()
    )

    assert application1 is not application2

    assert application1.agent_runtime is agent_runtime1
    assert application2.agent_runtime is agent_runtime2

    assert application1.execution_runtime is execution_runtime1
    assert application2.execution_runtime is execution_runtime2

    assert application1.get_agent("agent-1") is not application2.get_agent(
        "agent-2"
    )