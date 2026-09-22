import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.agents.agent_registry import AgentRegistry


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


def test_registry_can_register_agent():
    registry = AgentRegistry()
    agent = create_agent("agent-001")

    registry.register(agent)

    assert registry.get("agent-001") is agent
    assert registry.has("agent-001")


def test_registry_can_initialize_with_agents():
    agent_a = create_agent("agent-001")
    agent_b = create_agent("agent-002")

    registry = AgentRegistry(
        agents=[
            agent_a,
            agent_b,
        ]
    )

    assert registry.all() == (
        agent_a,
        agent_b,
    )


def test_registry_rejects_duplicate_agent_id():
    registry = AgentRegistry()

    registry.register(
        create_agent("agent-001")
    )

    with pytest.raises(
        ValueError,
        match="Agent already registered",
    ):
        registry.register(
            create_agent("agent-001")
        )


def test_registry_get_unknown_agent_raises_key_error():
    registry = AgentRegistry()

    with pytest.raises(
        KeyError,
        match="Agent not found",
    ):
        registry.get("unknown-agent")


def test_registry_has_unknown_agent_returns_false():
    registry = AgentRegistry()

    assert not registry.has("unknown-agent")


def test_registry_all_returns_immutable_view():
    agent = create_agent("agent-001")
    registry = AgentRegistry(
        agents=[agent]
    )

    agents = registry.all()

    assert isinstance(agents, tuple)
    assert agents == (agent,)


def test_registry_preserves_agent_instance_identity():
    agent = create_agent("agent-001")
    registry = AgentRegistry(
        agents=[agent]
    )

    assert registry.get("agent-001") is agent
    assert registry.all()[0] is agent