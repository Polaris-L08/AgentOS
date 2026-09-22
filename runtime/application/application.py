from __future__ import annotations

from typing import TYPE_CHECKING, Any

from models.task_result import TaskResult
from runtime.agents.agent_registry import AgentRegistry
from runtime.application.application_component import ApplicationComponent
from runtime.application.application_executor import ApplicationExecutor
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
    ApplicationState,
)
from runtime.checkpoint import (
    Checkpoint,
    CheckpointStore,
    MemoryCheckpointStore,
)
from runtime.events.event import Event
from runtime.events.publisher import EventPublisher
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.runtime_operation import RuntimeOperation
from runtime.orchestration import (
    Orchestrator,
    SingleAgentOrchestrator,
)
from runtime.persistence import (
    ExecutionStore,
    InMemoryExecutionStore,
    InMemorySessionStore,
    InMemoryTaskStore,
    SessionStore,
    TaskStore,
)
from runtime.persistence.postgres import PostgresDatabase
from runtime.session import (
    Session,
    SessionManager,
    SessionState,
)

if TYPE_CHECKING:
    from agents.agent_result import AgentResult
    from agents.base_agent import BaseAgent
    from models.task_request import TaskRequest
    from runtime.execution.agent_runtime import AgentRuntime
    from runtime.execution.execution_handle import ExecutionHandle
    from runtime.execution.execution_runtime import ExecutionRuntime


class AgentApplication:
    """
    Application-level runtime boundary.

    AgentApplication owns:
        - AgentRegistry
        - AgentRuntime
        - ExecutionRuntime
        - Orchestrator
        - SessionManager
        - Persistence stores
        - Application lifecycle

    AgentApplication coordinates runtime components but does not
    implement Agent execution logic itself.

    Agent registration and lookup are delegated to AgentRegistry.
    The existing add_agent(), get_agent(), has_agent(), and agents
    APIs remain as Application-level facade methods for compatibility.
    """

    def __init__(
        self,
        application_id: str,
        name: str,
        agent_runtime: AgentRuntime,
        execution_runtime: ExecutionRuntime,
        agent_registry: AgentRegistry | None = None,
        session_manager: SessionManager | None = None,
        publisher: EventPublisher | None = None,
        middleware_chain: MiddlewareChain | None = None,
        components: tuple[tuple[str, Any], ...] | None = None,
        session_store: SessionStore | None = None,
        execution_store: ExecutionStore | None = None,
        task_store: TaskStore | None = None,
        checkpoint_store: CheckpointStore | None = None,
        orchestrator: Orchestrator | None = None,
        owned_persistence_resources: tuple[
            PostgresDatabase,
            ...,
        ] | None = None,
    ) -> None:
        self.application_id = application_id
        self.name = name
        self.agent_runtime = agent_runtime
        self.execution_runtime = execution_runtime

        self.session_manager = (
            session_manager or SessionManager()
        )

        self.session_store = (
            session_store or InMemorySessionStore()
        )

        self.execution_store = (
            execution_store or InMemoryExecutionStore()
        )

        self.task_store = (
            task_store or InMemoryTaskStore()
        )

        self.checkpoint_store = (
            checkpoint_store or MemoryCheckpointStore()
        )

        self._owned_persistence_resources = tuple(
            owned_persistence_resources or ()
        )
        self._persistence_resources_closed = False

        self._publisher = publisher
        self._middleware_chain = middleware_chain

        self._components = tuple(components or ())

        self._initialized_components: list[
            tuple[str, ApplicationComponent]
        ] = []

        self._started_components: list[
            tuple[str, ApplicationComponent]
        ] = []

        self._agent_registry = (
            agent_registry or AgentRegistry()
        )

        if orchestrator is None:
            orchestrator = SingleAgentOrchestrator(
                agent_registry=self._agent_registry,
                agent_runtime=self.agent_runtime,
            )

        self._orchestrator = orchestrator
        self._state = ApplicationState.CREATED

        self._executor = ApplicationExecutor(
            application=self,
            execution_runtime=self.execution_runtime,
            orchestrator=self._orchestrator,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> ApplicationState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state == ApplicationState.RUNNING

    @property
    def agents(self) -> tuple[BaseAgent, ...]:
        return self._agent_registry.all()

    @property
    def agent_registry(self) -> AgentRegistry:
        return self._agent_registry

    @property
    def orchestrator(self) -> Orchestrator | None:
        return self._orchestrator

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        self._require_state(ApplicationState.CREATED)

        initialized: list[
            tuple[str, ApplicationComponent]
        ] = []

        try:
            for name, component in self._lifecycle_components():
                await component.initialize()
                initialized.append((name, component))
        except BaseException:
            await self._rollback_initialized_components(
                initialized
            )
            raise

        self._initialized_components = initialized
        self._state = ApplicationState.INITIALIZED

    async def start(self) -> None:
        self._require_state(ApplicationState.INITIALIZED)

        started: list[
            tuple[str, ApplicationComponent]
        ] = []

        try:
            for name, component in self._initialized_components:
                await component.start()
                started.append((name, component))
        except BaseException:
            await self._rollback_started_components(
                started
            )
            raise

        self._started_components = started
        self._state = ApplicationState.RUNNING

        await self._publish(
            Event(
                type="application.started",
                source="agent_application",
                payload={
                    "application_id": self.application_id,
                    "name": self.name,
                },
            )
        )

    async def stop(self) -> None:
        self._require_state(ApplicationState.RUNNING)

        self._state = ApplicationState.STOPPING

        try:
            await self._shutdown_components()
            await self._close_owned_persistence_resources()
        except BaseException:
            raise
        else:
            self._state = ApplicationState.STOPPED
            self._started_components.clear()
            self._initialized_components.clear()

            await self._publish(
                Event(
                    type="application.stopped",
                    source="agent_application",
                    payload={
                        "application_id": self.application_id,
                        "name": self.name,
                    },
                )
            )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        task: TaskRequest,
    ) -> TaskResult:
        """
        Execute a new logical Application Execution.
        """

        self._require_state(ApplicationState.RUNNING)
        self._validate_task_session(task)

        return await self._executor.execute(task)

    async def resume_execution(
        self,
        execution_id: str,
    ) -> TaskResult:
        """
        Resume a persisted logical Execution.

        This is the public Application-level crash/restart
        recovery API.

        The caller provides only the durable logical Execution
        identity.

        ApplicationExecutor reconstructs:
            Execution
            TaskRequest
            Checkpoint
            RuntimeContext
            Orchestration entry Agent
        """

        self._require_state(ApplicationState.RUNNING)

        return await self._executor.resume_persisted_execution(
            execution_id=execution_id,
        )

    # ------------------------------------------------------------------
    # Checkpoint persistence
    # ------------------------------------------------------------------

    async def persist_checkpoint(
        self,
        execution_handle: ExecutionHandle,
        checkpoint: Checkpoint,
    ) -> None:
        self._require_state(ApplicationState.RUNNING)

        await self._executor.persist_checkpoint(
            execution_handle=execution_handle,
            checkpoint=checkpoint,
        )

    # ------------------------------------------------------------------
    # Agent registry
    # ------------------------------------------------------------------

    def get_agent(self, agent_id: str) -> BaseAgent:
        return self._agent_registry.get(agent_id)

    def has_agent(self, agent_id: str) -> bool:
        return self._agent_registry.has(agent_id)

    # ------------------------------------------------------------------
    # Session validation
    # ------------------------------------------------------------------

    def _validate_task_session(
        self,
        task: TaskRequest,
    ) -> None:
        if task.session_id is None:
            return

        if not self.session_manager.has_session(
            task.session_id
        ):
            raise KeyError(
                f"Session not found: {task.session_id}"
            )

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    def create_session(
        self,
        metadata: dict | None = None,
    ) -> Session:
        self._require_state(ApplicationState.RUNNING)

        return self.session_manager.create_session(
            metadata=metadata
        )

    def get_session(
        self,
        session_id: str,
    ) -> Session:
        self._require_state(ApplicationState.RUNNING)

        return self.session_manager.get_session(
            session_id
        )

    def has_session(
        self,
        session_id: str,
    ) -> bool:
        self._require_state(ApplicationState.RUNNING)

        return self.session_manager.has_session(
            session_id
        )

    def delete_session(
        self,
        session_id: str,
    ) -> None:
        self._require_state(ApplicationState.RUNNING)

        self.session_manager.delete_session(
            session_id
        )

    async def persist_session(
        self,
        session_id: str,
    ) -> SessionState:
        self._require_state(ApplicationState.RUNNING)

        session = self.session_manager.get_session(
            session_id
        )

        state = session.snapshot()

        await self.session_store.save(state)

        return state

    # ------------------------------------------------------------------
    # Agent invocation
    # ------------------------------------------------------------------

    async def invoke_agent(
        self,
        agent_id: str,
        task: TaskRequest,
        execution_handle: ExecutionHandle,
    ) -> AgentResult:
        """
        Invoke an Agent through AgentRuntime.

        Application owns:
            - lifecycle validation
            - Agent resolution
            - Application middleware

        AgentRuntime owns:
            - AgentExecutionContext
            - Agent execution
            - Agent middleware
            - Agent lifecycle events

        This method remains as an Application-level compatibility
        facade. Orchestrator implementations should call
        AgentRuntime directly instead.
        """

        self._require_state(ApplicationState.RUNNING)

        agent = self.get_agent(agent_id)

        operation = RuntimeOperation(
            name="application.invoke_agent",
            component="agent_application",
            metadata={
                "application_id": self.application_id,
                "agent_id": agent.identity.agent_id,
                "agent_type": agent.identity.agent_type,
                "agent_name": agent.identity.name,
            },
        )

        if self._middleware_chain is None:
            return await self._invoke_agent(
                agent,
                task,
                execution_handle,
            )

        await self._middleware_chain.before(
            operation,
            execution_handle.runtime_context,
        )

        try:
            result = await self._invoke_agent(
                agent,
                task,
                execution_handle,
            )
        except Exception as error:
            await self._middleware_chain.on_error(
                operation,
                execution_handle.runtime_context,
                error,
            )
            raise
        else:
            await self._middleware_chain.after(
                operation,
                execution_handle.runtime_context,
                result,
            )
            return result

    async def _invoke_agent(
        self,
        agent: BaseAgent,
        task: TaskRequest,
        execution_handle: ExecutionHandle,
    ) -> AgentResult:
        return await self.agent_runtime.execute(
            agent=agent,
            task=task,
            runtime_context=execution_handle.runtime_context,
        )

    # ------------------------------------------------------------------
    # Internal component lifecycle
    # ------------------------------------------------------------------

    def _lifecycle_components(
        self,
    ) -> tuple[
        tuple[str, ApplicationComponent],
        ...
    ]:
        result: list[
            tuple[str, ApplicationComponent]
        ] = []

        for name, component in self._components:
            if (
                callable(
                    getattr(
                        component,
                        "initialize",
                        None,
                    )
                )
                and callable(
                    getattr(
                        component,
                        "start",
                        None,
                    )
                )
                and callable(
                    getattr(
                        component,
                        "stop",
                        None,
                    )
                )
            ):
                result.append(
                    (
                        name,
                        component,
                    )
                )

        return tuple(result)

    async def _rollback_initialized_components(
        self,
        initialized: list[
            tuple[str, ApplicationComponent]
        ],
    ) -> None:
        for _, component in reversed(initialized):
            try:
                await component.stop()
            except BaseException:
                pass

    async def _rollback_started_components(
        self,
        started: list[
            tuple[str, ApplicationComponent]
        ],
    ) -> None:
        for _, component in reversed(started):
            try:
                await component.stop()
            except BaseException:
                pass

    async def _shutdown_components(self) -> None:
        stopped: set[int] = set()

        for _, component in reversed(
            self._started_components
        ):
            await component.stop()
            stopped.add(id(component))

        for _, component in reversed(
            self._initialized_components
        ):
            if id(component) in stopped:
                continue

            await component.stop()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _publish(
        self,
        event: Event,
    ) -> None:
        if self._publisher is None:
            return

        self._publisher.emit(event)

    def _require_state(
        self,
        expected: ApplicationState,
    ) -> None:
        if self._state != expected:
            raise ApplicationLifecycleError(
                f"Application is in state '{self._state.value}', "
                f"expected '{expected.value}'."
            )

    async def _close_owned_persistence_resources(
        self,
    ) -> None:
        if self._persistence_resources_closed:
            return

        for resource in reversed(
            self._owned_persistence_resources
        ):
            await resource.close()

        self._persistence_resources_closed = True