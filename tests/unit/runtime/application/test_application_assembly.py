import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.agents.agent_registry import AgentRegistry
from runtime.application import (
    AgentApplication,
    ApplicationAssembly,
)
from runtime.application.application_config import (
    ApplicationConfig,
)
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.orchestration import (
    SingleAgentOrchestrator,
)
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


def create_runtime_services():
    agent_runtime = AgentRuntime()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    return agent_runtime, execution_runtime


def create_assembly() -> ApplicationAssembly:
    return ApplicationAssembly(
        config=ApplicationConfig(
            application_id="app-001",
            name="Test Application",
        )
    )


def test_assembly_can_register_agent_runtime():
    assembly = create_assembly()

    agent_runtime = AgentRuntime()

    assembly.register_component(
        "agent_runtime",
        agent_runtime,
    )

    assert (
        assembly.components.get("agent_runtime")
        is agent_runtime
    )


def test_assembly_can_register_execution_runtime():
    assembly = create_assembly()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    assembly.register_component(
        "execution_runtime",
        execution_runtime,
    )

    assert (
        assembly.components.get("execution_runtime")
        is execution_runtime
    )


def test_assembly_can_register_multiple_components():
    assembly = create_assembly()

    agent_runtime, execution_runtime = (
        create_runtime_services()
    )

    assembly.register_component(
        "agent_runtime",
        agent_runtime,
    )

    assembly.register_component(
        "execution_runtime",
        execution_runtime,
    )

    assert len(assembly.components) == 2


def test_assembly_can_add_agent():
    assembly = create_assembly()

    agent = create_agent("agent-001")

    assembly.add_agent(agent)

    assert len(assembly._agents) == 1
    assert assembly._agents[0] is agent


def test_assembly_rejects_duplicate_agent_id():
    assembly = create_assembly()

    agent1 = create_agent("agent-001")
    agent2 = create_agent("agent-001")

    assembly.add_agent(agent1)

    with pytest.raises(
        ValueError,
        match="Agent already registered in ApplicationAssembly",
    ):
        assembly.add_agent(agent2)


def test_assembly_requires_agent_runtime():
    assembly = create_assembly()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    assembly.register_component(
        "execution_runtime",
        execution_runtime,
    )

    with pytest.raises(
        ValueError,
        match="requires 'agent_runtime' component",
    ):
        assembly.build()


def test_assembly_requires_execution_runtime():
    assembly = create_assembly()

    agent_runtime = AgentRuntime()

    assembly.register_component(
        "agent_runtime",
        agent_runtime,
    )

    with pytest.raises(
        ValueError,
        match="requires 'execution_runtime' component",
    ):
        assembly.build()


def test_assembly_builds_application():
    assembly = create_assembly()

    agent_runtime, execution_runtime = (
        create_runtime_services()
    )

    agent = create_agent("agent-001")

    assembly.register_component(
        "agent_runtime",
        agent_runtime,
    )

    assembly.register_component(
        "execution_runtime",
        execution_runtime,
    )

    assembly.add_agent(agent)

    application = assembly.build()

    assert isinstance(
        application,
        AgentApplication,
    )

    assert application.application_id == "app-001"
    assert application.name == "Test Application"

    assert application.agent_runtime is agent_runtime
    assert application.execution_runtime is execution_runtime

    assert application.get_agent(
        "agent-001"
    ) is agent


def test_assembly_creates_agent_registry():
    assembly = create_assembly()

    agent_runtime, execution_runtime = (
        create_runtime_services()
    )

    agent = create_agent("agent-001")

    assembly.register_component(
        "agent_runtime",
        agent_runtime,
    )

    assembly.register_component(
        "execution_runtime",
        execution_runtime,
    )

    assembly.add_agent(agent)

    application = assembly.build()

    assert isinstance(
        application.agent_registry,
        AgentRegistry,
    )

    assert application.agent_registry.get(
        "agent-001"
    ) is agent


def test_assembly_registry_preserves_agent_instance_identity():
    assembly = create_assembly()

    agent_runtime, execution_runtime = (
        create_runtime_services()
    )

    agent = create_agent("agent-001")

    assembly.register_component(
        "agent_runtime",
        agent_runtime,
    )

    assembly.register_component(
        "execution_runtime",
        execution_runtime,
    )

    assembly.add_agent(agent)

    application = assembly.build()

    assert (
        application.agent_registry.get(
            "agent-001"
        )
        is agent
    )

    assert application.agents[0] is agent


def test_assembly_creates_default_single_agent_orchestrator():
    assembly = create_assembly()

    agent_runtime, execution_runtime = (
        create_runtime_services()
    )

    agent = create_agent("agent-001")

    assembly.register_component(
        "agent_runtime",
        agent_runtime,
    )

    assembly.register_component(
        "execution_runtime",
        execution_runtime,
    )

    assembly.add_agent(agent)

    application = assembly.build()

    assert isinstance(
        application.orchestrator,
        SingleAgentOrchestrator,
    )

    assert (
        application.orchestrator.agent_registry
        is application.agent_registry
    )

    assert (
        application.orchestrator.agent_runtime
        is application.agent_runtime
    )


def test_assembly_does_not_create_new_runtime_instances():
    assembly = create_assembly()

    agent_runtime, execution_runtime = (
        create_runtime_services()
    )

    assembly.register_component(
        "agent_runtime",
        agent_runtime,
    )

    assembly.register_component(
        "execution_runtime",
        execution_runtime,
    )

    application = assembly.build()

    assert application.agent_runtime is agent_runtime
    assert (
        application.execution_runtime
        is execution_runtime
    )