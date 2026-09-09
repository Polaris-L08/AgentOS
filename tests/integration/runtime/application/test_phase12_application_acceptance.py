from __future__ import annotations

import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from models.task_result import TaskResult
from runtime.application import AgentApplication
from runtime.checkpoint.checkpoint_coordinator import CheckpointCoordinator
from runtime.context.agent_execution_context import AgentExecutionContext
from runtime.events.event import Event
from runtime.events.event_bus import EventBus
from runtime.events.subscriber import EventSubscriber
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_handle import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.middleware.base_middleware import Middleware
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.runtime_operation import RuntimeOperation
from runtime.tracing.trace_recorder import TraceRecorder


# ============================================================================
# Test Agents
# ============================================================================


class AcceptanceAgent(BaseAgent):
    """
    Deterministic Agent used by the Phase12 acceptance tests.

    This Agent intentionally contains no business logic and no
    infrastructure dependency. Its purpose is to verify that the
    Application Runtime can correctly host an Agent.
    """

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output=f"processed: {task.user_input}",
            metadata={
                "agent_id": self.identity.agent_id,
            },
        )


class RecordingAgent(AcceptanceAgent):
    """
    Acceptance Agent that records invocation count.

    Used to prove that invalid Application-level requests are
    rejected before Agent execution begins.
    """

    def __init__(
        self,
        identity: AgentIdentity,
    ) -> None:
        super().__init__(identity)
        self.invocation_count = 0

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:
        self.invocation_count += 1

        return await super().run(
            task,
            agent_execution_context,
        )


# ============================================================================
# Test Middleware
# ============================================================================


class RecordingMiddleware(Middleware):
    """
    Middleware used to verify the Application-level middleware boundary.
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


# ============================================================================
# Test Event Subscriber
# ============================================================================


class RecordingSubscriber(EventSubscriber):
    """
    Subscriber used to verify Application lifecycle events.
    """

    def __init__(self) -> None:
        self.events: list[Event] = []

    def handle(
        self,
        event: Event,
    ) -> None:
        self.events.append(event)


# ============================================================================
# Application Factory
# ============================================================================


def create_application(
    *,
    agent: BaseAgent | None = None,
    publisher: EventBus | None = None,
    middleware_chain: MiddlewareChain | None = None,
) -> AgentApplication:
    """
    Create a deterministic Application for acceptance testing.
    """

    trace_recorder = TraceRecorder()

    execution_runtime = ExecutionRuntime(
        trace_recorder=trace_recorder,
    )

    agent_runtime = AgentRuntime()

    if agent is None:
        agent = AcceptanceAgent(
            identity=AgentIdentity(
                agent_id="acceptance-agent",
                agent_type="acceptance",
                name="Acceptance Agent",
            )
        )

    return AgentApplication(
        application_id="phase12-acceptance",
        name="Phase12 Acceptance Application",
        agent_runtime=agent_runtime,
        execution_runtime=execution_runtime,
        agents=[agent],
        publisher=publisher,
        middleware_chain=middleware_chain,
    )


async def start_application(
    application: AgentApplication,
) -> None:
    """
    Start an Application through its public lifecycle.
    """

    await application.initialize()
    await application.start()


# ============================================================================
# AC-1 / AC-2
# Application Assembly + Lifecycle
# ============================================================================


@pytest.mark.asyncio
async def test_phase12_application_assembly_and_lifecycle():
    """
    AC-1 + AC-2

    Verify that an Application can be assembled with its core
    Runtime components and move through the expected lifecycle:

        CREATED
            ↓
        INITIALIZED
            ↓
        RUNNING
            ↓
        STOPPING
            ↓
        STOPPED
    """

    application = create_application()

    assert application.state.value == "created"
    assert application.is_running is False

    await application.initialize()

    assert application.state.value == "initialized"
    assert application.is_running is False

    await application.start()

    assert application.state.value == "running"
    assert application.is_running is True

    await application.stop()

    assert application.state.value == "stopped"
    assert application.is_running is False


# ============================================================================
# AC-3
# Application Execution
# ============================================================================


@pytest.mark.asyncio
async def test_phase12_application_execute_returns_task_result():
    """
    AC-3

    Verify the complete public Application execution path:

        TaskRequest
            ↓
        Application.execute()
            ↓
        ApplicationExecutor
            ↓
        ExecutionRuntime
            ↓
        Application.invoke_agent()
            ↓
        AgentRuntime
            ↓
        AgentResult
            ↓
        TaskResult
    """

    application = create_application()

    await start_application(application)

    task = TaskRequest(
        task_id="phase12-task-001",
        user_input="Analyze NVIDIA",
    )

    result = await application.execute(task)

    assert isinstance(result, TaskResult)

    assert result.success is True
    assert result.answer == "processed: Analyze NVIDIA"

    assert result.metadata["task_id"] == "phase12-task-001"
    assert result.metadata["agent_id"] == "acceptance-agent"
    assert result.metadata["agent_type"] == "acceptance"

    await application.stop()


# ============================================================================
# AC-4
# Session × Execution
# ============================================================================


@pytest.mark.asyncio
async def test_phase12_session_can_be_reused_by_multiple_executions():
    """
    AC-4

    One Session may be associated with multiple independent
    Executions.

        Session
          ├── Execution #1
          └── Execution #2

    Session does not become the owner of the Execution lifecycle.
    """

    application = create_application()

    await start_application(application)

    session = application.create_session(
        metadata={
            "channel": "acceptance-test",
        }
    )

    task_1 = TaskRequest(
        task_id="phase12-session-task-001",
        user_input="first request",
        session_id=session.session_id,
    )

    task_2 = TaskRequest(
        task_id="phase12-session-task-002",
        user_input="second request",
        session_id=session.session_id,
    )

    result_1 = await application.execute(task_1)
    result_2 = await application.execute(task_2)

    assert result_1.success is True
    assert result_2.success is True

    assert result_1.answer == "processed: first request"
    assert result_2.answer == "processed: second request"

    assert application.has_session(
        session.session_id
    ) is True

    await application.stop()


@pytest.mark.asyncio
async def test_phase12_unknown_session_is_rejected_before_agent_execution():
    """
    AC-4

    Application must validate Session ownership before entering
    Agent execution.

    Therefore an invalid Session must not reach the Agent.
    """

    agent = RecordingAgent(
        identity=AgentIdentity(
            agent_id="recording-agent",
            agent_type="acceptance",
            name="Recording Agent",
        )
    )

    application = create_application(
        agent=agent,
    )

    await start_application(application)

    task = TaskRequest(
        task_id="phase12-invalid-session-task",
        user_input="should not execute",
        session_id="unknown-session",
    )

    with pytest.raises(
        KeyError,
        match="Session not found",
    ):
        await application.execute(task)

    assert agent.invocation_count == 0

    await application.stop()


@pytest.mark.asyncio
async def test_phase12_session_belongs_to_its_application():
    """
    AC-4

    A Session created by Application A cannot be used by
    Application B.
    """

    agent_a = RecordingAgent(
        identity=AgentIdentity(
            agent_id="agent-a",
            agent_type="acceptance",
            name="Agent A",
        )
    )

    agent_b = RecordingAgent(
        identity=AgentIdentity(
            agent_id="agent-b",
            agent_type="acceptance",
            name="Agent B",
        )
    )

    application_a = create_application(
        agent=agent_a,
    )

    application_b = create_application(
        agent=agent_b,
    )

    await start_application(application_a)
    await start_application(application_b)

    session = application_a.create_session()

    task = TaskRequest(
        task_id="cross-application-session",
        user_input="should be rejected",
        session_id=session.session_id,
    )

    with pytest.raises(
        KeyError,
        match="Session not found",
    ):
        await application_b.execute(task)

    assert agent_a.invocation_count == 0
    assert agent_b.invocation_count == 0

    await application_b.stop()
    await application_a.stop()


# ============================================================================
# AC-5
# Execution Recovery
# ============================================================================


@pytest.mark.asyncio
async def test_phase12_execution_recovery_preserves_execution_identity():
    """
    AC-5

    Verify:

        Checkpoint
            ↓
        ApplicationExecutor.recover_execution()
            ↓
        ExecutionRuntime.resume_execution()
            ↓
        recovered ExecutionHandle

    The Execution identity must survive recovery.
    """

    application = create_application()

    await start_application(application)

    original_handle = (
        application.execution_runtime.create_execution()
    )

    try:
        checkpoint_coordinator = CheckpointCoordinator()

        agent = application.agents[0]

        agent_execution_context = (
            AgentExecutionContext.create(
                runtime_context=original_handle.runtime_context,
                agent=agent,
            )
        )

        checkpoint = checkpoint_coordinator.create_checkpoint(
            runtime_context=original_handle.runtime_context,
            agent_execution_contexts={
                agent.identity.agent_id:
                    agent_execution_context,
            },
            task_id="phase12-recovery-task",
        )

        recovered_handle = (
            await application._executor.recover_execution(
                checkpoint
            )
        )

        try:
            assert isinstance(
                recovered_handle,
                ExecutionHandle,
            )

            assert recovered_handle.closed is False

            assert (
                recovered_handle.execution_id
                == checkpoint.runtime_id
            )

            assert (
                recovered_handle.runtime_context.runtime_id
                == original_handle.runtime_context.runtime_id
            )

        finally:
            await recovered_handle.close()

    finally:
        await original_handle.close()
        await application.stop()


@pytest.mark.asyncio
async def test_phase12_execution_recovery_creates_new_trace():
    """
    AC-5

    Execution identity survives recovery, but Trace identity
    starts a new tracing lifecycle.
    """

    application = create_application()

    await start_application(application)

    original_handle = (
        application.execution_runtime.create_execution()
    )

    try:
        original_trace_id = (
            original_handle
            .runtime_context
            .trace
            .trace
            .trace_id
        )

        checkpoint_coordinator = CheckpointCoordinator()

        agent = application.agents[0]

        agent_execution_context = (
            AgentExecutionContext.create(
                runtime_context=original_handle.runtime_context,
                agent=agent,
            )
        )

        checkpoint = checkpoint_coordinator.create_checkpoint(
            runtime_context=original_handle.runtime_context,
            agent_execution_contexts={
                agent.identity.agent_id:
                    agent_execution_context,
            },
            task_id="phase12-trace-recovery",
        )

        recovered_handle = (
            await application._executor.recover_execution(
                checkpoint
            )
        )

        try:
            recovered_trace_id = (
                recovered_handle
                .runtime_context
                .trace
                .trace
                .trace_id
            )

            assert recovered_trace_id != original_trace_id

        finally:
            await recovered_handle.close()

    finally:
        await original_handle.close()
        await application.stop()


@pytest.mark.asyncio
async def test_phase12_execution_recovery_restores_shared_context():
    """
    AC-5

    SharedContext is part of durable Execution state.

    Recovery must reconstruct a RuntimeContext containing
    the checkpointed SharedContext.
    """

    application = create_application()

    await start_application(application)

    original_handle = (
        application.execution_runtime.create_execution()
    )

    try:
        original_shared_context = (
            original_handle
            .runtime_context
            .shared_context
        )

        original_shared_context.set(
            "research_subject",
            "NVIDIA",
        )

        original_shared_context.set(
            "risk_level",
            "high",
        )

        checkpoint_coordinator = CheckpointCoordinator()

        agent = application.agents[0]

        agent_execution_context = (
            AgentExecutionContext.create(
                runtime_context=original_handle.runtime_context,
                agent=agent,
            )
        )

        checkpoint = checkpoint_coordinator.create_checkpoint(
            runtime_context=original_handle.runtime_context,
            agent_execution_contexts={
                agent.identity.agent_id:
                    agent_execution_context,
            },
            task_id="phase12-shared-context-recovery",
        )

        recovered_handle = (
            await application._executor.recover_execution(
                checkpoint
            )
        )

        try:
            recovered_shared_context = (
                recovered_handle
                .runtime_context
                .shared_context
            )

            assert (
                recovered_shared_context.get(
                    "research_subject"
                )
                == "NVIDIA"
            )

            assert (
                recovered_shared_context.get(
                    "risk_level"
                )
                == "high"
            )

        finally:
            await recovered_handle.close()

    finally:
        await original_handle.close()
        await application.stop()


# ============================================================================
# AC-6
# Agent Execution Context Recovery
# ============================================================================


@pytest.mark.asyncio
async def test_phase12_agent_checkpoint_restores_execution_state_on_live_agent():
    """
    AC-6

    Verify the boundary between durable Agent execution state and
    long-lived Agent capabilities.

    Checkpoint restores:

        state
        loop

    while the restored AgentExecutionContext obtains:

        AgentIdentity
        AgentContext
        MemoryRuntime

    from the existing live Agent.
    """

    application = create_application()

    await start_application(application)

    original_handle = (
        application.execution_runtime.create_execution()
    )

    try:
        agent = application.agents[0]

        original_agent_context = (
            AgentExecutionContext.create(
                runtime_context=original_handle.runtime_context,
                agent=agent,
            )
        )

        original_agent_context.loop.step_count = 7
        original_agent_context.loop.reflection_count = 2

        checkpoint_coordinator = CheckpointCoordinator()

        checkpoint = checkpoint_coordinator.create_checkpoint(
            runtime_context=original_handle.runtime_context,
            agent_execution_contexts={
                agent.identity.agent_id:
                    original_agent_context,
            },
            task_id="phase12-agent-recovery",
        )

        recovered_handle = (
            await application._executor.recover_execution(
                checkpoint
            )
        )

        try:
            restored_contexts = (
                checkpoint_coordinator.restore_agent_contexts(
                    checkpoint=checkpoint,
                    agents={
                        agent.identity.agent_id: agent,
                    },
                    runtime_context=recovered_handle.runtime_context,
                )
            )

            restored_context = restored_contexts[
                agent.identity.agent_id
            ]

            assert (
                restored_context.runtime_context
                is recovered_handle.runtime_context
            )

            assert (
                restored_context.agent_identity
                is agent.identity
            )

            assert (
                restored_context.agent_context
                is agent.context
            )

            assert (
                restored_context.memory
                is agent.memory
            )

            assert (
                restored_context.loop.step_count
                == 7
            )

            assert (
                restored_context.loop.reflection_count
                == 2
            )

        finally:
            await recovered_handle.close()

    finally:
        await original_handle.close()
        await application.stop()


# ============================================================================
# AC-7
# Application Middleware + Event Integration
# ============================================================================


@pytest.mark.asyncio
async def test_phase12_application_middleware_wraps_agent_invocation():
    """
    AC-7

    Application-level Middleware must surround the Application
    Agent invocation boundary.

        Application Middleware
                ↓
        Application.invoke_agent()
                ↓
            AgentRuntime
                ↓
              Agent
    """

    middleware = RecordingMiddleware()

    application = create_application(
        middleware_chain=MiddlewareChain(
            [middleware]
        ),
    )

    await start_application(application)

    execution_handle = (
        application.execution_runtime.create_execution()
    )

    try:
        task = TaskRequest(
            task_id="phase12-middleware-task",
            user_input="middleware test",
        )

        result = await application.invoke_agent(
            agent_id="acceptance-agent",
            task=task,
            execution_handle=execution_handle,
        )

        assert result.success is True
        assert result.output == "processed: middleware test"

        assert middleware.before_operations == [
            "application.invoke_agent"
        ]

        assert middleware.after_operations == [
            "application.invoke_agent"
        ]

        assert middleware.error_operations == []

        assert middleware.runtime_contexts == [
            execution_handle.runtime_context
        ]

    finally:
        await execution_handle.close()
        await application.stop()


@pytest.mark.asyncio
async def test_phase12_application_lifecycle_events_are_published():
    """
    AC-7

    Verify that Application lifecycle events remain visible
    through the EventBus.
    """

    event_bus = EventBus()

    subscriber = RecordingSubscriber()

    event_bus.subscribe(
        "application.started",
        subscriber,
    )

    event_bus.subscribe(
        "application.stopped",
        subscriber,
    )

    application = create_application(
        publisher=event_bus,
    )

    await application.initialize()
    await application.start()

    assert len(subscriber.events) == 1

    started_event = subscriber.events[0]

    assert started_event.type == "application.started"
    assert started_event.source == "agent_application"

    assert (
        started_event.payload["application_id"]
        == "phase12-acceptance"
    )

    await application.stop()

    assert len(subscriber.events) == 2

    stopped_event = subscriber.events[1]

    assert stopped_event.type == "application.stopped"
    assert stopped_event.source == "agent_application"

    assert (
        stopped_event.payload["application_id"]
        == "phase12-acceptance"
    )


# ============================================================================
# AC-8
# Final End-to-End Application Acceptance
# ============================================================================


@pytest.mark.asyncio
async def test_phase12_full_application_runtime_acceptance():
    """
    AC-8

    Final Phase12 integration test.

    This verifies the central Application Runtime path:

        Session
            ↓
        TaskRequest
            ↓
        AgentApplication
            ↓
        ApplicationExecutor
            ↓
        ExecutionRuntime
            ↓
        RuntimeContext
            ↓
        AgentRuntime
            ↓
        AgentExecutionContext
            ↓
        Agent
            ↓
        AgentResult
            ↓
        TaskResult

    The test intentionally uses a deterministic Agent so that
    Runtime behavior is tested independently of an external LLM.
    """

    event_bus = EventBus()

    middleware = RecordingMiddleware()

    application = create_application(
        publisher=event_bus,
        middleware_chain=MiddlewareChain(
            [middleware]
        ),
    )

    await application.initialize()

    assert application.state.value == "initialized"

    await application.start()

    assert application.is_running is True

    session = application.create_session(
        metadata={
            "purpose": "phase12-acceptance",
        }
    )

    task = TaskRequest(
        task_id="phase12-final-acceptance",
        user_input="Analyze NVIDIA risk",
        session_id=session.session_id,
    )

    result = await application.execute(task)

    # ------------------------------------------------------------------
    # Application result boundary
    # ------------------------------------------------------------------

    assert isinstance(result, TaskResult)

    assert result.success is True

    assert result.answer == (
        "processed: Analyze NVIDIA risk"
    )

    # ------------------------------------------------------------------
    # Task metadata
    # ------------------------------------------------------------------

    assert (
        result.metadata["task_id"]
        == "phase12-final-acceptance"
    )

    assert (
        result.metadata["agent_id"]
        == "acceptance-agent"
    )

    assert (
        result.metadata["agent_type"]
        == "acceptance"
    )

    # ------------------------------------------------------------------
    # Application lifecycle
    # ------------------------------------------------------------------

    assert application.is_running is True

    await application.stop()

    assert application.state.value == "stopped"
    assert application.is_running is False