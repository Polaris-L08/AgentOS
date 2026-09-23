from __future__ import annotations

import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.agents.agent_registry import AgentRegistry
from runtime.application import AgentApplication
from runtime.application.application_lifecycle import (
    ApplicationState,
)
from runtime.checkpoint import MemoryCheckpointStore
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.orchestration import SingleAgentOrchestrator
from runtime.persistence import (
    InMemoryExecutionStore,
    InMemorySessionStore, InMemoryTaskStore,
)
from runtime.session import SessionManager
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    async def run(
        self,
        task: TaskRequest,
        agent_execution_context,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output=f"processed: {task.user_input}",
        )


def create_agent(
    agent_id: str,
    agent_type: str = "mock",
    name: str | None = None,
) -> MockAgent:
    return MockAgent(
        identity=AgentIdentity(
            agent_id=agent_id,
            agent_type=agent_type,
            name=name or agent_id,
        )
    )


def create_application(
    agents: list[BaseAgent] | None = None,
) -> AgentApplication:
    agent_runtime = AgentRuntime()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    agent_registry = AgentRegistry(
        agents=agents or []
    )

    orchestrator = SingleAgentOrchestrator(
        agent_registry=agent_registry,
        agent_runtime=agent_runtime,
    )

    return AgentApplication(
        application_id="app-001",
        name="Test Application",
        agent_runtime=agent_runtime,
        execution_runtime=execution_runtime,
        agent_registry=agent_registry,
        session_manager=SessionManager(),
        publisher=None,
        middleware_chain=None,
        components=(),
        session_store=InMemorySessionStore(),
        execution_store=InMemoryExecutionStore(),
        task_store=InMemoryTaskStore(),
        checkpoint_store=MemoryCheckpointStore(),
        orchestrator=orchestrator,
        owned_persistence_resources=(),
    )


def test_application_exposes_agents_from_registry():
    agent = create_agent("agent-001")

    application = create_application(
        agents=[agent]
    )

    assert application.has_agent("agent-001")
    assert application.get_agent("agent-001") is agent
    assert application.agents == (agent,)


def test_application_exposes_multiple_agents_from_registry():
    agent_a = create_agent(
        "agent-001",
        name="Agent A",
    )

    agent_b = create_agent(
        "agent-002",
        name="Agent B",
    )

    application = create_application(
        agents=[
            agent_a,
            agent_b,
        ]
    )

    assert application.agents == (
        agent_a,
        agent_b,
    )

    assert application.get_agent("agent-001") is agent_a
    assert application.get_agent("agent-002") is agent_b


def test_application_does_not_expose_add_agent_api():
    application = create_application()

    assert not hasattr(
        application,
        "add_agent",
    )


def test_application_get_unknown_agent_raises_key_error():
    application = create_application()

    with pytest.raises(
        KeyError,
        match="Agent not found",
    ):
        application.get_agent("unknown-agent")


def test_application_agents_cannot_mutate_internal_collection():
    agent = create_agent("agent-001")

    application = create_application(
        agents=[agent]
    )

    agents = application.agents

    assert isinstance(
        agents,
        tuple,
    )

    assert agents == (agent,)


def test_application_exposes_agent_registry():
    agent = create_agent("agent-001")

    application = create_application(
        agents=[agent]
    )

    assert isinstance(
        application.agent_registry,
        AgentRegistry,
    )

    assert (
        application.agent_registry.get("agent-001")
        is agent
    )


def test_application_preserves_agent_instance_identity():
    agent = create_agent("agent-001")

    application = create_application(
        agents=[agent]
    )

    first = application.get_agent("agent-001")
    second = application.get_agent("agent-001")

    assert first is second
    assert first is agent


def test_different_applications_can_use_different_agent_registries():
    agent_a = create_agent("agent-001")
    agent_b = create_agent("agent-001")

    application_a = create_application(
        agents=[agent_a]
    )

    application_b = create_application(
        agents=[agent_b]
    )

    assert (
        application_a.agent_registry
        is not application_b.agent_registry
    )

    assert (
        application_a.get_agent("agent-001")
        is agent_a
    )

    assert (
        application_b.get_agent("agent-001")
        is agent_b
    )


def test_application_owns_runtime_services():
    agent_runtime = AgentRuntime()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    agent_registry = AgentRegistry()

    orchestrator = SingleAgentOrchestrator(
        agent_registry=agent_registry,
        agent_runtime=agent_runtime,
    )

    application = AgentApplication(
        application_id="app-001",
        name="Test Application",
        agent_runtime=agent_runtime,
        execution_runtime=execution_runtime,
        agent_registry=agent_registry,
        session_manager=SessionManager(),
        publisher=None,
        middleware_chain=None,
        components=(),
        session_store=InMemorySessionStore(),
        execution_store=InMemoryExecutionStore(),
        task_store=__import__(
            "runtime.persistence",
            fromlist=["InMemoryTaskStore"],
        ).InMemoryTaskStore(),
        checkpoint_store=MemoryCheckpointStore(),
        orchestrator=orchestrator,
        owned_persistence_resources=(),
    )

    assert application.agent_runtime is agent_runtime
    assert application.execution_runtime is execution_runtime


def test_application_preserves_injected_dependencies():
    agent_runtime = AgentRuntime()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    agent_registry = AgentRegistry()

    session_manager = SessionManager()
    session_store = InMemorySessionStore()
    execution_store = InMemoryExecutionStore()
    task_store = __import__(
        "runtime.persistence",
        fromlist=["InMemoryTaskStore"],
    ).InMemoryTaskStore()
    checkpoint_store = MemoryCheckpointStore()

    orchestrator = SingleAgentOrchestrator(
        agent_registry=agent_registry,
        agent_runtime=agent_runtime,
    )

    application = AgentApplication(
        application_id="app-001",
        name="Test Application",
        agent_runtime=agent_runtime,
        execution_runtime=execution_runtime,
        agent_registry=agent_registry,
        session_manager=session_manager,
        publisher=None,
        middleware_chain=None,
        components=(),
        session_store=session_store,
        execution_store=execution_store,
        task_store=task_store,
        checkpoint_store=checkpoint_store,
        orchestrator=orchestrator,
        owned_persistence_resources=(),
    )

    assert application.agent_registry is agent_registry
    assert application.session_manager is session_manager
    assert application.session_store is session_store
    assert application.execution_store is execution_store
    assert application.task_store is task_store
    assert application.checkpoint_store is checkpoint_store
    assert application.orchestrator is orchestrator


def test_application_starts_in_created_state():
    application = create_application()

    assert application.state == ApplicationState.CREATED
    assert application.is_running is False


def test_application_requires_assembled_dependencies():
    """
    AgentApplication 不能脱离 Composition Root 随意创建默认基础设施。
    """
    agent_runtime = AgentRuntime()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    with pytest.raises(
        TypeError,
    ):
        AgentApplication(
            application_id="app-001",
            name="Test Application",
            agent_runtime=agent_runtime,
            execution_runtime=execution_runtime,
        )