import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
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


class MockAgent(BaseAgent):
    async def run(self, task, agent_execution_context):
        return f"processed: {task.user_input}"


class RecordingSubscriber(EventSubscriber):
    def __init__(self) -> None:
        self.events: list[Event] = []

    def handle(self, event: Event) -> None:
        self.events.append(event)


class RecordingMiddleware(Middleware):
    def __init__(self) -> None:
        self.before_operations: list[str] = []
        self.after_operations: list[str] = []
        self.error_operations: list[str] = []

    async def before(
        self,
        operation: RuntimeOperation,
        runtime_context,
    ) -> None:
        self.before_operations.append(operation.name)

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


class FailingAgent(BaseAgent):
    async def run(self, task, agent_execution_context):
        raise RuntimeError("agent failed")


def create_application(
    *,
    publisher=None,
    middleware_chain=None,
    failing_agent=False,
):
    trace_recorder = TraceRecorder()

    agent_runtime = AgentRuntime()

    if failing_agent:
        agent = FailingAgent(
            identity=AgentIdentity(
                agent_id="agent-1",
                agent_type="failing",
                name="Failing Agent",
            )
        )
    else:
        agent = MockAgent(
            identity=AgentIdentity(
                agent_id="agent-1",
                agent_type="mock",
                name="Mock Agent",
            )
        )

    return AgentApplication(
        application_id="app-1",
        name="Test Application",
        agent_runtime=agent_runtime,
        execution_runtime=ExecutionRuntime(
            trace_recorder=trace_recorder,
        ),
        agents=[agent],
        publisher=publisher,
        middleware_chain=middleware_chain,
    )


@pytest.mark.asyncio
async def test_application_publishes_started_event():
    event_bus = EventBus()
    subscriber = RecordingSubscriber()

    event_bus.subscribe(
        "application.started",
        subscriber,
    )

    application = create_application(
        publisher=event_bus,
    )

    await application.initialize()
    await application.start()

    assert len(subscriber.events) == 1

    event = subscriber.events[0]

    assert event.type == "application.started"
    assert event.source == "agent_application"
    assert event.payload["application_id"] == "app-1"
    assert event.payload["name"] == "Test Application"


@pytest.mark.asyncio
async def test_application_publishes_stopped_event():
    event_bus = EventBus()
    subscriber = RecordingSubscriber()

    event_bus.subscribe(
        "application.stopped",
        subscriber,
    )

    application = create_application(
        publisher=event_bus,
    )

    await application.initialize()
    await application.start()
    await application.stop()

    assert len(subscriber.events) == 1

    event = subscriber.events[0]

    assert event.type == "application.stopped"
    assert event.source == "agent_application"
    assert event.payload["application_id"] == "app-1"


@pytest.mark.asyncio
async def test_application_does_not_require_event_publisher():
    application = create_application()

    await application.initialize()
    await application.start()
    await application.stop()

    assert application.state.value == "stopped"


@pytest.mark.asyncio
async def test_application_middleware_runs_before_and_after_agent_invocation():
    middleware = RecordingMiddleware()

    application = create_application(
        middleware_chain=MiddlewareChain([middleware]),
    )

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    result = await application.invoke_agent(
        agent_id="agent-1",
        task=task,
        execution_handle=execution,
    )

    assert result.success is True
    assert result.output == "processed: hello"

    assert middleware.before_operations == [
        "application.invoke_agent"
    ]

    assert middleware.after_operations == [
        "application.invoke_agent"
    ]

    assert middleware.error_operations == []


@pytest.mark.asyncio
async def test_application_middleware_receives_same_runtime_context():
    class ContextRecordingMiddleware(Middleware):
        def __init__(self) -> None:
            self.runtime_context = None

        async def before(
            self,
            operation,
            runtime_context,
        ):
            self.runtime_context = runtime_context

        async def after(
            self,
            operation,
            runtime_context,
            result,
        ):
            assert runtime_context is self.runtime_context

        async def on_error(
            self,
            operation,
            runtime_context,
            error,
        ):
            assert runtime_context is self.runtime_context

    middleware = ContextRecordingMiddleware()

    application = create_application(
        middleware_chain=MiddlewareChain([middleware]),
    )

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    await application.invoke_agent(
        agent_id="agent-1",
        task=TaskRequest(
            task_id="task-1",
            user_input="hello",
        ),
        execution_handle=execution,
    )

    assert middleware.runtime_context is execution.runtime_context


@pytest.mark.asyncio
async def test_application_middleware_on_error_runs_when_agent_fails():
    middleware = RecordingMiddleware()

    application = create_application(
        middleware_chain=MiddlewareChain([middleware]),
        failing_agent=True,
    )

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    with pytest.raises(RuntimeError, match="agent failed"):
        await application.invoke_agent(
            agent_id="agent-1",
            task=TaskRequest(
                task_id="task-1",
                user_input="hello",
            ),
            execution_handle=execution,
        )

    assert middleware.before_operations == [
        "application.invoke_agent"
    ]

    assert middleware.after_operations == []

    assert middleware.error_operations == [
        "application.invoke_agent"
    ]


@pytest.mark.asyncio
async def test_application_middleware_does_not_replace_agent_runtime_middleware():
    application_middleware = RecordingMiddleware()
    agent_middleware = RecordingMiddleware()

    agent_runtime = AgentRuntime(
        middleware_chain=MiddlewareChain([agent_middleware]),
    )

    agent = MockAgent(
        identity=AgentIdentity(
            agent_id="agent-1",
            agent_type="mock",
            name="Mock Agent",
        )
    )

    application = AgentApplication(
        application_id="app-1",
        name="Test Application",
        agent_runtime=agent_runtime,
        execution_runtime=ExecutionRuntime(
            trace_recorder=TraceRecorder(),
        ),
        agents=[agent],
        middleware_chain=MiddlewareChain(
            [application_middleware]
        ),
    )

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    result = await application.invoke_agent(
        agent_id="agent-1",
        task=TaskRequest(
            task_id="task-1",
            user_input="hello",
        ),
        execution_handle=execution,
    )

    assert result.success is True

    assert application_middleware.before_operations == [
        "application.invoke_agent"
    ]

    assert application_middleware.after_operations == [
        "application.invoke_agent"
    ]

    assert agent_middleware.before_operations == [
        "agent.execute"
    ]

    assert agent_middleware.after_operations == [
        "agent.execute"
    ]


@pytest.mark.asyncio
async def test_application_middleware_runs_outside_agent_runtime_middleware():
    call_order: list[str] = []

    class ApplicationMiddleware(Middleware):
        async def before(self, operation, runtime_context):
            call_order.append("application.before")

        async def after(self, operation, runtime_context, result):
            call_order.append("application.after")

        async def on_error(self, operation, runtime_context, error):
            call_order.append("application.error")

    class AgentMiddleware(Middleware):
        async def before(self, operation, runtime_context):
            call_order.append("agent.before")

        async def after(self, operation, runtime_context, result):
            call_order.append("agent.after")

        async def on_error(self, operation, runtime_context, error):
            call_order.append("agent.error")

    agent = MockAgent(
        identity=AgentIdentity(
            agent_id="agent-1",
            agent_type="mock",
            name="Mock Agent",
        )
    )

    agent_runtime = AgentRuntime(
        middleware_chain=MiddlewareChain(
            [AgentMiddleware()]
        ),
    )

    application = AgentApplication(
        application_id="app-1",
        name="Test Application",
        agent_runtime=agent_runtime,
        execution_runtime=ExecutionRuntime(
            trace_recorder=TraceRecorder(),
        ),
        agents=[agent],
        middleware_chain=MiddlewareChain(
            [ApplicationMiddleware()]
        ),
    )

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    await application.invoke_agent(
        agent_id="agent-1",
        task=TaskRequest(
            task_id="task-1",
            user_input="hello",
        ),
        execution_handle=execution,
    )

    assert call_order == [
        "application.before",
        "agent.before",
        "agent.after",
        "application.after",
    ]


@pytest.mark.asyncio
async def test_application_does_not_close_execution_after_agent_invocation():
    application = create_application()

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    await application.invoke_agent(
        agent_id="agent-1",
        task=TaskRequest(
            task_id="task-1",
            user_input="hello",
        ),
        execution_handle=execution,
    )

    assert execution.closed is False


@pytest.mark.asyncio
async def test_application_events_and_agent_events_can_share_event_bus():
    event_bus = EventBus()
    subscriber = RecordingSubscriber()

    event_bus.subscribe(
        "application.started",
        subscriber,
    )

    event_bus.subscribe(
        "agent.started",
        subscriber,
    )

    event_bus.subscribe(
        "agent.completed",
        subscriber,
    )

    application = create_application(
        publisher=event_bus,
    )

    # The current Application owns the AgentRuntime instance.
    # Reuse the same EventBus for AgentRuntime event publication.
    application.agent_runtime._publisher = event_bus

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    await application.invoke_agent(
        agent_id="agent-1",
        task=TaskRequest(
            task_id="task-1",
            user_input="hello",
        ),
        execution_handle=execution,
    )

    assert [
        event.type for event in subscriber.events
    ] == [
        "application.started",
        "agent.started",
        "agent.completed",
    ]