from __future__ import annotations

from typing import TYPE_CHECKING, Any

from models.task_result import TaskResult
from runtime.application.application_component import ApplicationComponent
from runtime.application.application_executor import ApplicationExecutor
from runtime.application.application_lifecycle import ApplicationState, ApplicationLifecycleError
from runtime.checkpoint import CheckpointStore, MemoryCheckpointStore
from runtime.events.event import Event
from runtime.events.publisher import EventPublisher
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.runtime_operation import RuntimeOperation
from runtime.persistence import SessionStore, ExecutionStore, InMemorySessionStore, InMemoryExecutionStore
from runtime.persistence.postgres import PostgresDatabase
from runtime.session import SessionManager, Session, SessionState

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent
    from agents.agent_result import AgentResult
    from models.task_request import TaskRequest
    from runtime.execution.agent_runtime import AgentRuntime
    from runtime.execution.execution_runtime import ExecutionRuntime
    from runtime.execution.execution_handle import ExecutionHandle


class AgentApplication:
    """
    Application-level runtime boundary.

    AgentApplication owns:

        - Agents
        - AgentRuntime
        - ExecutionRuntime
        - SessionManager
        - Application lifecycle

    AgentApplication coordinates runtime components but does not
    implement Agent execution logic itself.
    """
    def __init__(
            self,
            application_id: str,
            name: str,
            agent_runtime: AgentRuntime,
            execution_runtime: ExecutionRuntime,
            agents: list[BaseAgent] | None = None,
            session_manager: SessionManager | None = None,
            publisher: EventPublisher | None = None,
            middleware_chain: MiddlewareChain | None = None,
            components: tuple[tuple[str, Any],...] | None = None,
            session_store: SessionStore | None = None,
            execution_store: ExecutionStore | None = None,
            checkpoint_store: CheckpointStore | None = None,
            owned_persistence_resources: tuple[PostgresDatabase, ...] | None = None,
    ) -> None:
        self.application_id = application_id
        self.name = name
        self.agent_runtime = agent_runtime
        self.execution_runtime = execution_runtime

        self.session_manager = session_manager or SessionManager()

        self.session_store = session_store or InMemorySessionStore()
        self.execution_store = execution_store or InMemoryExecutionStore()
        self.checkpoint_store = checkpoint_store or MemoryCheckpointStore()

        self._owned_persistence_resources  = tuple(owned_persistence_resources or ())
        self._persistence_resources_closed = False

        self._publisher = publisher
        self._middleware_chain = middleware_chain

        # ApplicationAssembly provides a stable snapshot.
        # The Application owns that snapshot for lifecycle orchestration.
        self._components = tuple(components or ())

        self._initialized_components: list[tuple[str, ApplicationComponent]] = []

        self._started_components: list[tuple[str, ApplicationComponent]] = []

        self._agents: dict[str, BaseAgent] = {}

        self._state = ApplicationState.CREATED

        for agent in agents or []:
            self.add_agent(agent)

        self._executor = ApplicationExecutor(
            application=self,
            execution_runtime=self.execution_runtime,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> ApplicationState:
        """
        Current Application lifecycle state.
        """
        return self._state

    @property
    def is_running(self) -> bool:
        """
        Return True when the Application is accepting runtime work.
        """
        return self._state == ApplicationState.RUNNING

    @property
    def agents(self) -> tuple[BaseAgent, ...]:
        """
        Return all Agent instances owned by this Application.

        A tuple is returned so callers cannot mutate the internal
        Application ownership collection directly.
        """

        return tuple(self._agents.values())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """
        Initialize the Application.

        Valid transition:

            CREATED → INITIALIZED

        Initialization is intentionally limited to the Application
        lifecycle state in this lesson.

        Component-specific initialization will be introduced later
        when Application Assembly is implemented.
        """
        self._require_state(ApplicationState.CREATED)

        initialized: list[tuple[str, ApplicationComponent]] = []

        try:
            for name, component in self._lifecycle_components():
                await component.initialize()
                initialized.append((name, component))
        except BaseException:
            await self._rollback_initialized_components(initialized)
            raise

        self._initialized_components = initialized
        self._state = ApplicationState.INITIALIZED

    async def start(self) -> None:
        """
        Start the Application.

        Valid transition:

            INITIALIZED → RUNNING
        """
        self._require_state(ApplicationState.INITIALIZED)

        started: list[tuple[str, ApplicationComponent]] = []

        try:
            for name, component in self._initialized_components:
                await component.start()
                started.append((name, component))
        except BaseException:
            await self._rollback_started_components(started)
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
                }
            )
        )

    async def stop(self) -> None:
        """
        Stop the Application.

        Valid transition:

            RUNNING → STOPPING → STOPPED

        The STOPPING state exists to provide a correct lifecycle
        boundary for future graceful shutdown behavior.

        Actual draining/cancellation of executions and component
        shutdown will be introduced in later lessons.
        """
        self._require_state(ApplicationState.RUNNING)

        self._state = ApplicationState.STOPPING

        try:
            await self._shutdown_components()
            await self._close_owned_persistence_resources()
        except BaseException:
            # The Application lifecycle must not silently return to
            # RUNNING after shutdown has started.
            #
            # The state remains STOPPING so callers can observe that
            # shutdown did not complete successfully.
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
                    }
                )
            )

    async def execute(
            self,
            task: TaskRequest,
    ) -> TaskResult:
        """
        Public Application execution API.

        Application owns the public execution boundary while
        ApplicationExecutor owns the internal execution lifecycle.
        """
        self._require_state(ApplicationState.RUNNING)

        self._validate_task_session(task)

        return await self._executor.execute(task)

    # ------------------------------------------------------------------
    # Agent ownership
    # ------------------------------------------------------------------

    def add_agent(self, agent: BaseAgent) -> None:
        """
        Add an Agent instance to this Application.

        The Application becomes the owner of the Agent instance.

        Agent instances are keyed by their stable AgentIdentity.agent_id.
        """

        agent_id = agent.identity.agent_id

        if agent_id in self._agents:
            raise ValueError(
                f"Agent already exists in Application: {agent_id}"
            )

        self._agents[agent_id] = agent

    def get_agent(self, agent_id: str) -> BaseAgent:
        """
        Return an Agent instance owned by this Application.

        Raises:
            KeyError:
                If the Agent does not exist.
        """

        try:
            return self._agents[agent_id]
        except KeyError:
            raise KeyError(
                f"Agent not found in Application: {agent_id}"
            ) from None

    def has_agent(self, agent_id: str) -> bool:
        """
        Check whether an Agent is owned by this Application.
        """

        return agent_id in self._agents

    # ------------------------------------------------------------------
    # Session validation
    # ------------------------------------------------------------------
    def _validate_task_session(self, task: TaskRequest) -> None:
        """
        Validate the Session referenced by a TaskRequest.

        A task without a session_id is a valid stateless execution.

        When a session_id is provided, the Session must be owned by
        this Application.
        """
        if task.session_id is None:
            return

        if not self.session_manager.has_session(task.session_id):
            raise KeyError(
                f"Session not found: {task.session_id}"
            )

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------
    def create_session(self, metadata: dict | None = None) -> Session:
        """
        Create a new Session owned by this Application.

        Sessions can only be created while the Application is running.
        """

        self._require_state(ApplicationState.RUNNING)

        return self.session_manager.create_session(
            metadata=metadata
        )

    def get_session(self, session_id: str) -> Session:
        """
        Return a Session owned by this Application.

        Sessions are only accessible while the Application is running.
        """

        self._require_state(ApplicationState.RUNNING)

        return self.session_manager.get_session(
            session_id
        )

    def has_session(self, session_id: str) -> bool:
        """
        Return whether the Application owns the given Session.

        This method is intentionally lifecycle-aware.
        """

        self._require_state(ApplicationState.RUNNING)

        return self.session_manager.has_session(
            session_id
        )

    def delete_session(self, session_id: str) -> None:
        """
        Delete a Session owned by this Application.
        """

        self._require_state(ApplicationState.RUNNING)

        self.session_manager.delete_session(
            session_id
        )

    async def persist_session(self, session_id: str) -> SessionState:
        """
        Persist an existing Session.

        The live Session remains owned by SessionManager.
        Persistence stores its durable representation only.
        """
        self._require_state(ApplicationState.RUNNING)

        session = self.session_manager.get_session(session_id)

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
        Invoke an Agent through the Application-owned AgentRuntime.

        This is an Application coordination boundary.

        Application is responsible for:

            - Application lifecycle validation
            - Agent resolution
            - Application-level middleware

        AgentRuntime remains responsible for:

            - AgentExecutionContext
            - Agent execution
            - Agent middleware
            - Agent lifecycle events
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
            return await self._invoke_agent(agent, task, execution_handle)

        await self._middleware_chain.before(operation,execution_handle.runtime_context)

        try:
            result = await self._invoke_agent(agent, task, execution_handle)
        except Exception as error:
            await self._middleware_chain.on_error(
                operation,
                execution_handle.runtime_context,
                error
            )
            raise
        else:
            await self._middleware_chain.after(
                operation,
                execution_handle.runtime_context,
                result
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

    def _lifecycle_components(self) -> tuple[tuple[str, ApplicationComponent], ...]:
        """
        Return components participating in Application lifecycle
        management.

        Runtime components do not need to implement Application
        lifecycle.

        Only components providing the complete lifecycle contract
        are orchestrated here.
        """

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
        """
        Release components that initialized successfully before a
        later component failed initialization.

        Rollback is best-effort and never masks the original failure.
        """

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
        """
        Stop components that started successfully before a later
        component failed startup.

        The Application remains INITIALIZED when rollback succeeds,
        allowing the caller to retry startup.
        """

        for _, component in reversed(started):
            try:
                await component.stop()
            except BaseException:
                pass

    async def _shutdown_components(self) -> None:
        """
        Stop all Application lifecycle components in reverse startup
        order.

        Components that were initialized but never started are also
        stopped so initialization resources are released.
        """

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

    async def _publish(self, event: Event) -> None:
        if self._publisher is None:
            return
        self._publisher.emit(event)

    def _require_state(self, expected: ApplicationState) -> None:
        """
        Validate the current Application lifecycle state.
        """
        if self._state != expected:
            raise ApplicationLifecycleError(
                f"Application is in state '{self._state.value}', "
                f"expected '{expected.value}'."
            )

    async def _close_owned_persistence_resources(self) -> None:
        """
        Close persistence resources owned by this Application.

        Only resources explicitly transferred to the Application by
        ApplicationAssembly are closed here.

        Externally supplied persistence stores are not affected.
        """

        if self._persistence_resources_closed:
            return

        for resource in reversed(
                self._owned_persistence_resources
        ):
            await resource.close()

        self._persistence_resources_closed = True