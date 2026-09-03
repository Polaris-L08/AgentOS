import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from agents.agent_result import AgentResult
from models.task_request import TaskRequest
from runtime.application import AgentApplication
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
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

    return AgentApplication(
        application_id="app-001",
        name="Test Application",
        agent_runtime=AgentRuntime(),
        execution_runtime=ExecutionRuntime(
            trace_recorder=TraceRecorder()
        ),
        agents=agents,
    )


def test_application_owns_agent_instances():
    agent = create_agent("agent-001")

    application = create_application(
        agents=[agent]
    )

    assert application.has_agent("agent-001")

    assert application.get_agent("agent-001") is agent

    assert application.agents == (agent,)


def test_application_can_own_multiple_agent_instances():
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


def test_application_rejects_duplicate_agent_id():
    agent_a = create_agent("agent-001")
    agent_b = create_agent("agent-001")

    application = create_application(
        agents=[agent_a]
    )

    with pytest.raises(
        ValueError,
        match="Agent already exists in Application",
    ):
        application.add_agent(agent_b)


def test_application_get_unknown_agent_raises_key_error():
    application = create_application()

    with pytest.raises(
        KeyError,
        match="Agent not found in Application",
    ):
        application.get_agent("unknown-agent")


def test_application_agents_cannot_mutate_internal_collection():
    agent = create_agent("agent-001")

    application = create_application(
        agents=[agent]
    )

    agents = application.agents

    assert isinstance(agents, tuple)

    assert agents == (agent,)


def test_application_owns_runtime_services():
    agent_runtime = AgentRuntime()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    application = AgentApplication(
        application_id="app-001",
        name="Test Application",
        agent_runtime=agent_runtime,
        execution_runtime=execution_runtime,
    )

    assert application.agent_runtime is agent_runtime
    assert application.execution_runtime is execution_runtime


def test_application_preserves_agent_instance_identity():
    agent = create_agent("agent-001")

    application = create_application(
        agents=[agent]
    )

    first = application.get_agent("agent-001")
    second = application.get_agent("agent-001")

    assert first is second


def test_different_applications_can_own_different_agent_instances():
    agent_a = create_agent("agent-001")
    agent_b = create_agent("agent-001")

    application_a = create_application(
        agents=[agent_a]
    )

    application_b = create_application(
        agents=[agent_b]
    )

    assert application_a.get_agent("agent-001") is agent_a
    assert application_b.get_agent("agent-001") is agent_b

    assert (
        application_a.get_agent("agent-001")
        is not
        application_b.get_agent("agent-001")
    )