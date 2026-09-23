from __future__ import annotations

import inspect

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from runtime.agents.agent_registry import AgentRegistry
from runtime.application.application import AgentApplication
from runtime.application.application_executor import ApplicationExecutor
from runtime.execution.execution import Execution
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.orchestration.orchestrator import Orchestrator
from runtime.orchestration.single_agent_orchestrator import (
    SingleAgentOrchestrator,
)


class StubAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str = "stub-agent",
    ) -> None:
        super().__init__(
            identity=AgentIdentity(
                agent_id=agent_id,
                agent_type="stub",
                name="Stub Agent",
            )
        )

    async def run(
        self,
        task,
        context,
    ):
        return "ok"


def test_application_does_not_expose_add_agent_api() -> None:
    assert not hasattr(AgentApplication, "add_agent")


def test_application_exposes_registry_as_read_only_agent_facade() -> None:
    assert hasattr(AgentApplication, "agents")
    assert hasattr(AgentApplication, "agent_registry")
    assert hasattr(AgentApplication, "get_agent")
    assert hasattr(AgentApplication, "has_agent")


def test_application_executor_does_not_depend_on_application() -> None:
    signature = inspect.signature(ApplicationExecutor.__init__)

    assert "application" not in signature.parameters


def test_orchestrator_does_not_depend_on_application() -> None:
    signature = inspect.signature(Orchestrator.__init__)

    assert "application" not in signature.parameters


def test_single_agent_orchestrator_does_not_depend_on_application() -> None:
    signature = inspect.signature(
        SingleAgentOrchestrator.__init__
    )

    assert "application" not in signature.parameters


def test_application_executor_depends_on_runtime_and_persistence_boundaries() -> None:
    signature = inspect.signature(ApplicationExecutor.__init__)

    expected_parameters = {
        "execution_runtime",
        "orchestrator",
        "execution_store",
        "task_store",
        "checkpoint_store",
    }

    assert expected_parameters.issubset(signature.parameters)


def test_single_agent_orchestrator_depends_on_agent_registry_and_agent_runtime() -> None:
    signature = inspect.signature(
        SingleAgentOrchestrator.__init__
    )

    expected_parameters = {
        "agent_registry",
        "agent_runtime",
    }

    assert expected_parameters.issubset(signature.parameters)


def test_orchestrator_does_not_own_execution_runtime() -> None:
    signature = inspect.signature(Orchestrator.__init__)

    assert "execution_runtime" not in signature.parameters


def test_orchestrator_does_not_own_persistence_stores() -> None:
    signature = inspect.signature(Orchestrator.__init__)

    forbidden_parameters = {
        "execution_store",
        "task_store",
        "checkpoint_store",
        "session_store",
    }

    assert forbidden_parameters.isdisjoint(signature.parameters)


def test_agent_registry_is_the_application_agent_collection_boundary() -> None:
    registry = AgentRegistry(
        agents=[
            StubAgent("agent-1"),
            StubAgent("agent-2"),
        ]
    )

    assert registry.has("agent-1")
    assert registry.has("agent-2")
    assert registry.all() == registry.agents
    assert len(registry.agents) == 2


def test_application_executor_does_not_expose_legacy_recover_agent_execution() -> None:
    assert not hasattr(
        ApplicationExecutor,
        "recover_agent_execution",
    )


def test_application_executor_exposes_persisted_execution_recovery_api() -> None:
    assert hasattr(
        ApplicationExecutor,
        "recover_persisted_execution",
    )

    assert hasattr(
        ApplicationExecutor,
        "resume_persisted_execution",
    )


def test_execution_and_runtime_context_have_distinct_identity_concepts() -> None:
    execution_signature = inspect.signature(
        Execution.__init__
    )

    assert "execution_id" in execution_signature.parameters

    runtime_signature = inspect.signature(
        ExecutionRuntime.create_execution
    )

    assert "execution" in runtime_signature.parameters


def test_application_invoke_agent_is_a_direct_agent_runtime_facade() -> None:
    source = inspect.getsource(
        AgentApplication.invoke_agent
    )

    assert "agent_runtime.execute" in source
    assert "orchestrator.execute" not in source