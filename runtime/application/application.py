from __future__ import annotations

from typing import TYPE_CHECKING

from models.task_result import TaskResult
from runtime.application.application_lifecycle import ApplicationState, ApplicationLifecycleError
from runtime.events.event import Event
from runtime.events.publisher import EventPublisher
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.runtime_operation import RuntimeOperation
from runtime.session import SessionManager, Session

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
    ) -> None:
        self.application_id = application_id
        self.name = name
        self.agent_runtime = agent_runtime
        self.execution_runtime = execution_runtime

        self.session_manager = session_manager or SessionManager()

        self._publisher = publisher
        self._middleware_chain = middleware_chain

        self._agents: dict[str, BaseAgent] = {}

        self._state = ApplicationState.CREATED

        for agent in agents or []:
            self.add_agent(agent)

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

        self._state = ApplicationState.INITIALIZED

    async def start(self) -> None:
        """
        Start the Application.

        Valid transition:

            INITIALIZED → RUNNING
        """
        self._require_state(ApplicationState.INITIALIZED)

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
        except Exception:
            # The Application lifecycle must not silently return to
            # RUNNING after shutdown has started.
            #
            # The state remains STOPPING so callers can observe that
            # shutdown did not complete successfully.
            raise
        else:
            self._state = ApplicationState.STOPPED

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
            agent_id: str,
    ) -> TaskResult:
        """
        Execute one TaskRequest through an Agent.

        Application is responsible for the execution boundary.

        AgentRuntime is responsible for Agent invocation.

        Flow:

            TaskRequest
                ↓
            RuntimeContext
                ↓
            AgentRuntime
                ↓
            Agent
                ↓
            AgentResult
                ↓
            TaskResult

        RuntimeContext is created for this execution only.
        """
        self._require_state(ApplicationState.RUNNING)

        agent = self.get_agent(agent_id)

        runtime_context = self.execution_runtime.create_context()

        try:
            agent_result = await self.agent_runtime.execute(
                agent=agent,
                task=task,
                runtime_context=runtime_context,
            )
            return TaskResult(
                success=agent_result.success,
                answer=str(agent_result.output),
                metadata={
                    "agent_id": agent.identity.agent_id,
                    "agent_type": agent.identity.agent_type,
                },
            )
        finally:
            await self.execution_runtime.close(runtime_context)

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
    # Internal helpers
    # ------------------------------------------------------------------

    async def _publish(self, event: Event) -> None:
        if self._publisher is None:
            return
        self._publisher.emit(event)

    async def _shutdown_components(self) -> None:
        """
        Application component shutdown hook.

        There are currently no Application-owned components with a
        service-level shutdown lifecycle.

        This method intentionally remains empty until later lessons
        introduce Application Assembly and component lifecycle
        orchestration.
        """
        return

    def _require_state(self, expected: ApplicationState) -> None:
        """
        Require the Application to be in the expected state.

        Raises:
            ApplicationLifecycleError:
                If the requested lifecycle operation is invalid.
        """

        if self._state is not expected:
            raise ApplicationLifecycleError(
                f"Invalid Application lifecycle state: "
                f"expected '{expected.value}', "
                f"actual '{self._state.value}'."
            )