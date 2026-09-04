from __future__ import annotations

from agents.base_agent import BaseAgent
from runtime.application.application import AgentApplication
from runtime.application.component_registry import ComponentRegistry


class ApplicationAssembly:
    """
    Composition root for an AgentOS Application.

    ApplicationAssembly is responsible for:

        - registering Application components
        - registering Agent instances
        - building AgentApplication

    It does NOT:

        - execute Agents
        - manage RuntimeContext
        - manage AgentExecutionContext
        - run application lifecycle
    """

    def __init__(
        self,
        application_id: str,
        name: str,
    ) -> None:
        self._application_id = application_id
        self._name = name

        self._components = ComponentRegistry()
        self._agents: list[BaseAgent] = []

    @property
    def components(self) -> ComponentRegistry:
        return self._components

    def register_component(
        self,
        name: str,
        component,
    ) -> ApplicationAssembly:
        self._components.register(name, component)
        return self

    def add_agent(
        self,
        agent: BaseAgent,
    ) -> ApplicationAssembly:
        agent_id = agent.identity.agent_id

        if any(
            existing.identity.agent_id == agent_id
            for existing in self._agents
        ):
            raise ValueError(
                f"Agent already registered in ApplicationAssembly: "
                f"{agent_id}"
            )

        self._agents.append(agent)
        return self

    def build(self) -> AgentApplication:
        """
        Build an AgentApplication from the assembled components.

        Required components:

            - agent_runtime
            - execution_runtime
        """

        if not self._components.contains("agent_runtime"):
            raise ValueError(
                "ApplicationAssembly requires "
                "'agent_runtime' component."
            )

        if not self._components.contains("execution_runtime"):
            raise ValueError(
                "ApplicationAssembly requires "
                "'execution_runtime' component."
            )

        application = AgentApplication(
            application_id=self._application_id,
            name=self._name,
            agent_runtime=self._components.get("agent_runtime"),
            execution_runtime=self._components.get("execution_runtime"),
            agents=list(self._agents),
        )

        return application