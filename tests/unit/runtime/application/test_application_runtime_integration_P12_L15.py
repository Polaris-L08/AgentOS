import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from models.task_result import TaskResult
from runtime.application.application import AgentApplication
from runtime.events.event import Event
from runtime.events.event_bus import EventBus
from runtime.events.subscriber import EventSubscriber
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.middleware.base_middleware import Middleware
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.runtime_operation import RuntimeOperation
from runtime.tracing.trace_recorder import TraceRecorder


class RecordingAgent(BaseAgent):
    """
    Agent used to verify the Application → AgentRuntime execution boundary.
    """

    def __init__(self, identity: AgentIdentity) -> None:
        super().__init__(identity=identity)
        self.execution_contexts = []

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context,
    ) -> AgentResult:
        self.execution_contexts.append(agent_execution_context)

        return AgentResult(
            success=True,
            output=f"processed: {task.user_input}",
        )


class FailingAgent(BaseAgent):
    """
    Agent used to verify Application failure propagation.
    """

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context,
    ) -> AgentResult:
        raise RuntimeError("agent execution failed")


class RecordingMiddleware(Middleware):
    """
    Application-level middleware recorder.
    """

    def __init__(self) -> None:
        self.before_operations: list[str] = []
        self.after_operations: list[str] = []
        self.error_operations: list[str] = []
        self.runtime_contexts = []

    async def before(
        self,
        operation: RuntimeOperation,
        runtime_context,
    ) -> None:
        self.before_operations.append(operation.name)
        self.runtime_contexts.append(runtime_context)

    async def after(
        self,
        operation: RuntimeOperation,
        runtime_context,
        result,
    ) -> None:
        self.after_operations.append(operation.name)

    async def on_error(
        self,
        operation: RuntimeOperation,
        runtime_context,
        error: Exception,
    ) -> None:
        self.error_operations.append(operation.name)


class RecordingSubscriber(EventSubscriber):
    """
    Event subscriber used to verify Application + Agent events.
    """

    def __init__(self) -> None:
        self.events: list[Event] = []

    def handle(self, event: Event) -> None:
        self.events.append(event)


def create_application(
    agent: BaseAgent,
    *,
    publisher: EventBus | None = None,
    middleware_chain: MiddlewareChain | None = None,
) -> AgentApplication:
    """
    Build an Application with the runtime capabilities required by
    Lesson15 integration tests.
    """

    return AgentApplication(
        application_id="app-001",
        name="Integration Application",
        agent_runtime=AgentRuntime(
            publisher=publisher,
        ),
        execution_runtime=ExecutionRuntime(
            trace_recorder=TraceRecorder(),
        ),
        agents=[agent],
        publisher=publisher,
        middleware_chain=middleware_chain,
    )


async def start_application(
    application: AgentApplication,
) -> None:
    await application.initialize()
    await application.start()


@pytest.mark.asyncio
async def test_application_runtime_integration_executes_task_through_complete_boundary():
    agent = RecordingAgent(
        AgentIdentity(
            agent_id="agent-001",
            agent_type="integration",
            name="Integration Agent",
        )
    )

    middleware = RecordingMiddleware()

    application = create_application(
        agent,
        middleware_chain=MiddlewareChain(
            [middleware]
        ),
    )

    await start_application(application)

    result = await application.execute(
        TaskRequest(
            task_id="task-001",
            user_input="hello",
        )
    )

    assert isinstance(result, TaskResult)
    assert result.success is True
    assert result.answer == "processed: hello"

    assert result.metadata == {
        "task_id": "task-001",
        "agent_id": "agent-001",
        "agent_type": "integration",
    }

    assert middleware.before_operations == [
        "application.invoke_agent"
    ]

    assert middleware.after_operations == [
        "application.invoke_agent"
    ]

    assert middleware.error_operations == []

    assert len(agent.execution_contexts) == 1

    await application.stop()


@pytest.mark.asyncio
async def test_application_runtime_integration_preserves_runtime_context_across_application_and_agent_boundary():
    agent = RecordingAgent(
        AgentIdentity(
            agent_id="agent-001",
            agent_type="integration",
            name="Integration Agent",
        )
    )

    middleware = RecordingMiddleware()

    application = create_application(
        agent,
        middleware_chain=MiddlewareChain(
            [middleware]
        ),
    )

    await start_application(application)

    await application.execute(
        TaskRequest(
            task_id="task-001",
            user_input="hello",
        )
    )

    assert len(middleware.runtime_contexts) == 1
    assert len(agent.execution_contexts) == 1

    application_runtime_context = (
        middleware.runtime_contexts[0]
    )

    agent_runtime_context = (
        agent.execution_contexts[0].runtime_context
    )

    assert agent_runtime_context is application_runtime_context

    await application.stop()


@pytest.mark.asyncio
async def test_application_runtime_integration_supports_multiple_executions_in_one_session():
    agent = RecordingAgent(
        AgentIdentity(
            agent_id="agent-001",
            agent_type="integration",
            name="Integration Agent",
        )
    )

    application = create_application(agent)

    await start_application(application)

    session = application.create_session(
        metadata={
            "purpose": "integration-test"
        }
    )

    result_1 = await application.execute(
        TaskRequest(
            task_id="task-001",
            user_input="first",
            session_id=session.session_id,
        )
    )

    result_2 = await application.execute(
        TaskRequest(
            task_id="task-002",
            user_input="second",
            session_id=session.session_id,
        )
    )

    assert result_1.success is True
    assert result_1.answer == "processed: first"

    assert result_2.success is True
    assert result_2.answer == "processed: second"

    assert len(agent.execution_contexts) == 2

    runtime_context_1 = (
        agent.execution_contexts[0].runtime_context
    )

    runtime_context_2 = (
        agent.execution_contexts[1].runtime_context
    )

    assert runtime_context_1 is not runtime_context_2

    assert (
        runtime_context_1.runtime_id
        != runtime_context_2.runtime_id
    )

    assert application.has_session(
        session.session_id
    ) is True

    assert (
        application.get_session(
            session.session_id
        ).session_id
        == session.session_id
    )

    await application.stop()


@pytest.mark.asyncio
async def test_application_runtime_integration_rejects_unknown_session_before_agent_execution():
    agent = RecordingAgent(
        AgentIdentity(
            agent_id="agent-001",
            agent_type="integration",
            name="Integration Agent",
        )
    )

    application = create_application(agent)

    await start_application(application)

    with pytest.raises(
        KeyError,
        match="Session not found",
    ):
        await application.execute(
            TaskRequest(
                task_id="task-001",
                user_input="hello",
                session_id="unknown-session",
            )
        )

    assert agent.execution_contexts == []

    await application.stop()


@pytest.mark.asyncio
async def test_application_runtime_integration_propagates_agent_failure_and_runs_application_middleware_error_path():
    agent = FailingAgent(
        AgentIdentity(
            agent_id="agent-001",
            agent_type="failing",
            name="Failing Agent",
        )
    )

    middleware = RecordingMiddleware()

    application = create_application(
        agent,
        middleware_chain=MiddlewareChain(
            [middleware]
        ),
    )

    await start_application(application)

    with pytest.raises(
        RuntimeError,
        match="agent execution failed",
    ):
        await application.execute(
            TaskRequest(
                task_id="task-001",
                user_input="hello",
            )
        )

    assert middleware.before_operations == [
        "application.invoke_agent"
    ]

    assert middleware.after_operations == []

    assert middleware.error_operations == [
        "application.invoke_agent"
    ]

    assert application.is_running is True

    await application.stop()


@pytest.mark.asyncio
async def test_application_runtime_integration_publishes_application_and_agent_events():
    event_bus = EventBus()
    subscriber = RecordingSubscriber()

    for event_type in (
        "application.started",
        "agent.started",
        "agent.completed",
        "application.stopped",
    ):
        event_bus.subscribe(
            event_type,
            subscriber,
        )

    agent = RecordingAgent(
        AgentIdentity(
            agent_id="agent-001",
            agent_type="integration",
            name="Integration Agent",
        )
    )

    application = create_application(
        agent,
        publisher=event_bus,
    )

    await start_application(application)

    await application.execute(
        TaskRequest(
            task_id="task-001",
            user_input="hello",
        )
    )

    await application.stop()

    assert [
        event.type
        for event in subscriber.events
    ] == [
        "application.started",
        "agent.started",
        "agent.completed",
        "application.stopped",
    ]

    agent_started = subscriber.events[1]
    agent_completed = subscriber.events[2]

    assert (
        agent_started.payload["agent_id"]
        == "agent-001"
    )

    assert (
        agent_completed.payload["agent_id"]
        == "agent-001"
    )