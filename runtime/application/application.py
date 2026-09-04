from __future__ import annotations

from agents.base_agent import BaseAgent
from models.task_request import TaskRequest
from models.task_result import TaskResult
from runtime.application.application_lifecycle import ApplicationState, ApplicationLifecycleError
from runtime.execution import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime


class AgentApplication:
    """
    Application-level boundary for an AgentOS application.

    Application owns long-lived Agent instances and the runtime
    services used by those agents.

    Lifecycle:

        Application
            |
            +---- Agent instances
            |
            +---- AgentRuntime
            |
            +---- ExecutionRuntime

    Application does NOT execute an Agent directly.

    Agent invocation remains the responsibility of AgentRuntime.

    Execution-specific state remains the responsibility of
    ExecutionRuntime / RuntimeContext.

    Session and Application lifecycle management will be added
    in later Phase12 lessons.
    """
    def __init__(
            self,
            application_id: str,
            name: str,
            agent_runtime: AgentRuntime,
            execution_runtime: ExecutionRuntime,
            agents: list[BaseAgent] | None = None,
    ) -> None:
        self.application_id = application_id
        self.name = name
        self.agent_runtime = agent_runtime
        self.execution_runtime = execution_runtime

        self._agents: dict[str, BaseAgent] = {}

        self._state = ApplicationState.CREATED

        for agent in agents or []:
            self.add_agent(agent)

    # ------------------------------------------------------------------
    # Lifecycle
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

    @property
    def agents(self) -> tuple[BaseAgent, ...]:
        """
        Return all Agent instances owned by this Application.

        A tuple is returned so callers cannot mutate the internal
        Application ownership collection directly.
        """

        return tuple(self._agents.values())

    def has_agent(self, agent_id: str) -> bool:
        """
        Check whether an Agent is owned by this Application.
        """

        return agent_id in self._agents

    # ------------------------------------------------------------------
    # Internal lifecycle validation
    # ------------------------------------------------------------------

    def _require_state(self, expected: ApplicationState) -> None:
        """
        Require the Application to be in the expected state.

        Raises:
            ApplicationLifecycleError:
                If the requested lifecycle operation is invalid.
        """

        if self._state != expected:
            raise ApplicationLifecycleError(
                "Invalid Application lifecycle transition: "
                f"operation requires state '{expected.value}', "
                f"but current state is '{self._state.value}'."
            )