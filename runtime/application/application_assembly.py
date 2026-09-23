from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from runtime.agents.agent_registry import AgentRegistry
from runtime.application.application import AgentApplication
from runtime.application.application_config import ApplicationConfig
from runtime.application.component_registry import ComponentRegistry
from runtime.orchestration import (
    Orchestrator,
    SingleAgentOrchestrator,
)
from runtime.persistence import (
    PersistenceConfig,
    PersistenceStoreFactory,
)
from runtime.session import SessionManager


class ApplicationAssembly:
    """
    Composition root for an AgentOS Application.

    ApplicationAssembly assembles already-created runtime components.

    It does not:
        - implement runtime behavior
        - manage Application lifecycle
        - implement Agent orchestration
        - manage persistence lifecycle directly

    ApplicationAssembly is responsible for constructing the
    AgentRegistry and wiring it into the Application and
    Orchestrator.
    """

    def __init__(
        self,
        config: ApplicationConfig,
        persistence_config: PersistenceConfig | None = None,
    ) -> None:
        self._config = config

        self._persistence_config = (
            persistence_config or PersistenceConfig()
        )

        self._components = ComponentRegistry()
        self._agents: list[BaseAgent] = []

    @property
    def config(self) -> ApplicationConfig:
        return self._config

    @property
    def persistence_config(self) -> PersistenceConfig:
        return self._persistence_config

    @property
    def components(self) -> ComponentRegistry:
        return self._components

    @property
    def agents(self) -> tuple[BaseAgent, ...]:
        return tuple(self._agents)

    def register_component(
        self,
        name: str,
        component: Any,
    ) -> ApplicationAssembly:
        self._components.register(
            name,
            component,
        )
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
                "Agent already registered in "
                f"ApplicationAssembly: {agent_id}"
            )

        self._agents.append(agent)

        return self

    def build(self) -> AgentApplication:
        """
        Build an AgentApplication from assembled components.

        ApplicationAssembly is the Composition Root.

        It is responsible for:
            - resolving required runtime components
            - creating default infrastructure components
            - creating the AgentRegistry
            - creating the default Orchestrator
            - creating persistence stores
            - injecting all dependencies into AgentApplication

        AgentApplication receives fully assembled dependencies and
        does not create runtime infrastructure by itself.

        Required components:
            - agent_runtime
            - execution_runtime

        Optional components:
            - publisher
            - middleware
            - session_manager
            - session_store
            - execution_store
            - task_store
            - checkpoint_store
            - orchestrator
        """

        agent_runtime = self._get_required_component(
            "agent_runtime"
        )

        execution_runtime = self._get_required_component(
            "execution_runtime"
        )

        publisher = self._get_optional_component(
            "publisher"
        )

        middleware = self._get_optional_component(
            "middleware"
        )

        session_manager = self._get_optional_component(
            "session_manager"
        )

        if session_manager is None:
            session_manager = SessionManager()

        orchestrator = self._get_optional_component(
            "orchestrator"
        )

        session_store = self._get_optional_component(
            "session_store"
        )

        execution_store = self._get_optional_component(
            "execution_store"
        )

        task_store = self._get_optional_component(
            "task_store"
        )

        checkpoint_store = self._get_optional_component(
            "checkpoint_store"
        )

        owned_persistence_resources = ()

        missing_session_store = (
                session_store is None
        )

        missing_execution_store = (
                execution_store is None
        )

        missing_task_store = (
                task_store is None
        )

        missing_checkpoint_store = (
                checkpoint_store is None
        )

        if (
                missing_session_store
                or missing_execution_store
                or missing_task_store
                or missing_checkpoint_store
        ):
            bundle = (
                PersistenceStoreFactory.create_store_bundle(
                    self._persistence_config,
                    create_session_store=(
                        missing_session_store
                    ),
                    create_execution_store=(
                        missing_execution_store
                    ),
                    create_task_store=(
                        missing_task_store
                    ),
                    create_checkpoint_store=(
                        missing_checkpoint_store
                    ),
                )
            )

            if session_store is None:
                session_store = bundle.session_store

            if execution_store is None:
                execution_store = bundle.execution_store

            if task_store is None:
                task_store = bundle.task_store

            if checkpoint_store is None:
                checkpoint_store = bundle.checkpoint_store

            owned_persistence_resources = (
                bundle.resources
            )

        if session_store is None:
            raise RuntimeError(
                "ApplicationAssembly failed to create "
                "SessionStore."
            )

        if execution_store is None:
            raise RuntimeError(
                "ApplicationAssembly failed to create "
                "ExecutionStore."
            )

        if task_store is None:
            raise RuntimeError(
                "ApplicationAssembly failed to create "
                "TaskStore."
            )

        if checkpoint_store is None:
            raise RuntimeError(
                "ApplicationAssembly failed to create "
                "CheckpointStore."
            )

        agent_registry = AgentRegistry(
            agents=list(self._agents)
        )

        if orchestrator is None:
            orchestrator = SingleAgentOrchestrator(
                agent_registry=agent_registry,
                agent_runtime=agent_runtime,
            )
        elif not isinstance(
                orchestrator,
                Orchestrator,
        ):
            raise TypeError(
                "ApplicationAssembly orchestrator must be "
                "an Orchestrator instance."
            )

        application = AgentApplication(
            application_id=(
                self._config.application_id
            ),
            name=self._config.name,
            agent_runtime=agent_runtime,
            execution_runtime=execution_runtime,
            agent_registry=agent_registry,
            session_manager=session_manager,
            publisher=publisher,
            middleware_chain=middleware,
            components=self._components.items(),
            session_store=session_store,
            execution_store=execution_store,
            task_store=task_store,
            checkpoint_store=checkpoint_store,
            orchestrator=orchestrator,
            owned_persistence_resources=(
                owned_persistence_resources
            ),
        )

        return application

    def _get_required_component(
        self,
        name: str,
    ) -> Any:
        if not self._components.contains(name):
            raise ValueError(
                f"ApplicationAssembly requires "
                f"'{name}' component."
            )

        return self._components.get(name)

    def _get_optional_component(
        self,
        name: str,
    ) -> Any:
        if not self._components.contains(name):
            return None

        return self._components.get(name)