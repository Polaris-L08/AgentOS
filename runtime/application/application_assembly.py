from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from runtime.application.application import AgentApplication
from runtime.application.application_config import ApplicationConfig
from runtime.application.component_registry import ComponentRegistry


class ApplicationAssembly:
    """
    Composition root for an AgentOS Application.

    ApplicationAssembly is responsible for assembling already-created
    runtime components into an AgentApplication.

    It is not a dependency injection container and does not manage
    runtime lifecycle.
    """

    def __init__(
            self,
            config: ApplicationConfig,
    ) -> None:
        self._config = config

        self._components = ComponentRegistry()
        self._agents: list[BaseAgent] = []

    @property
    def config(self) -> ApplicationConfig:
        return self._config

    @property
    def components(self) -> ComponentRegistry:
        return self._components

    @property
    def agents(self) -> tuple[BaseAgent,...]:
        return tuple(self._agents)

    def register_component(
        self,
        name: str,
        component: Any,
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
                f"Agent already registered in ApplicationAssembly: {agent_id}"
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

        agent_runtime = self._get_required_component("agent_runtime")
        execution_runtime = self._get_required_component("execution_runtime")

        publisher = self._get_optional_component("publisher")
        middleware = self._get_optional_component("middleware")
        session_manager = self._get_optional_component("session_manager")

        application = AgentApplication(
            application_id=self._config.application_id,
            name=self._config.name,
            agent_runtime=self._components.get("agent_runtime"),
            execution_runtime=self._components.get("execution_runtime"),
            agents=list(self._agents),
            session_manager=session_manager,
            publisher=publisher,
            middleware_chain=middleware,
            components=self._components.items(),
        )

        return application

    def _get_required_component(self, name: str) -> Any:
        if not self._components.contains(name):
            raise ValueError(f"ApplicationAssembly requires {name} component.")

        return self._components.get(name)

    def _get_optional_component(self, name: str) -> Any:
        if not self._components.contains(name):
            return None
        return self._components.get(name)