from __future__ import annotations

import pytest

from agents import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.application.application import AgentApplication
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.execution.execution_state import ExecutionStatus
from runtime.persistence import (
    ExecutionStore,
    InMemoryExecutionStore,
    InMemorySessionStore,
    SessionStore,
)
from runtime.tracing.trace_recorder import TraceRecorder


class SuccessfulAgent(BaseAgent):
    """
    Deterministic Agent used by persistence tests.

    The Agent does not depend on an LLM or external Tool.
    """

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output="execution completed",
            metadata={
                "agent_id": self.identity.agent_id,
            },
        )


class FailingAgent(BaseAgent):
    """
    Deterministic Agent that always raises an exception.
    """

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context,
    ) -> AgentResult:
        raise RuntimeError("test agent failure")


def create_application(
    agent: BaseAgent,
    session_store: SessionStore | None = None,
    execution_store: ExecutionStore | None = None,
) -> AgentApplication:
    """
    Create a minimal Application for persistence tests.

    No external infrastructure is required.
    """

    return AgentApplication(
        application_id="test-application",
        name="Test Application",
        agent_runtime=AgentRuntime(),
        execution_runtime=ExecutionRuntime(
            TraceRecorder()
        ),
        agents=[agent],
        session_store=session_store,
        execution_store=execution_store,
    )


@pytest.fixture
def successful_application() -> AgentApplication:
    """
    Create an Application with a deterministic successful Agent.

    Application lifecycle is intentionally not started here because
    initialize/start/stop are asynchronous operations.
    """

    return create_application(
        SuccessfulAgent(
            identity=AgentIdentity(
                agent_id="successful-agent",
                agent_type="test-agent",
                name="SuccessfulAgent",
            )
        )
    )


@pytest.fixture
def failing_application() -> AgentApplication:
    """
    Create an Application with a deterministic failing Agent.
    """

    return create_application(
        FailingAgent(
            identity=AgentIdentity(
                agent_id="failing-agent",
                agent_type="test-agent",
                name="FailingAgent",
            )
        )
    )


@pytest.mark.asyncio
async def test_application_persists_session(
    successful_application: AgentApplication,
) -> None:
    """
    Application can explicitly persist a Session as SessionState.
    """

    application = successful_application

    await application.initialize()
    await application.start()

    try:
        session = application.create_session(
            metadata={
                "key": "value",
            }
        )

        state = await application.persist_session(
            session.session_id
        )

        assert state.session_id == session.session_id
        assert state.metadata == {
            "key": "value",
        }

        loaded = await application.session_store.load(
            session.session_id
        )

        assert loaded is not None
        assert loaded.session_id == session.session_id
        assert loaded.metadata == {
            "key": "value",
        }

    finally:
        await application.stop()


@pytest.mark.asyncio
async def test_application_uses_injected_session_store() -> None:
    """
    AgentApplication uses the SessionStore supplied by the caller.
    """

    session_store = InMemorySessionStore()

    application = create_application(
        SuccessfulAgent(
            identity=AgentIdentity(
                agent_id="session-store-agent",
                agent_type="test-agent",
                name="SessionStoreAgent",
            )
        ),
        session_store=session_store,
    )

    assert application.session_store is session_store

    await application.initialize()
    await application.start()

    try:
        session = application.create_session()

        await application.persist_session(
            session.session_id
        )

        loaded = await session_store.load(
            session.session_id
        )

        assert loaded is not None
        assert loaded.session_id == session.session_id

    finally:
        await application.stop()


@pytest.mark.asyncio
async def test_application_defaults_to_in_memory_persistence() -> None:
    """
    Application uses in-memory stores when no stores are supplied.
    """

    application = create_application(
        SuccessfulAgent(
            identity=AgentIdentity(
                agent_id="default-store-agent",
                agent_type="test-agent",
                name="DefaultStoreAgent",
            )
        )
    )

    assert isinstance(
        application.session_store,
        InMemorySessionStore,
    )

    assert isinstance(
        application.execution_store,
        InMemoryExecutionStore,
    )


@pytest.mark.asyncio
async def test_execution_lifecycle_is_persisted(
    successful_application: AgentApplication,
) -> None:
    """
    A successful Application execution persists the logical
    Execution lifecycle.

    Expected final state:

        CREATED
        RUNNING
        COMPLETED
    """

    application = successful_application

    await application.initialize()
    await application.start()

    try:
        task = TaskRequest(
            task_id="task-001",
            user_input="test execution",
        )

        result = await application.execute(
            task
        )

        assert result.success is True
        assert result.answer == "execution completed"

        states = application.execution_store._states

        assert len(states) == 1

        execution_id = next(iter(states))

        state = await application.execution_store.load(
            execution_id
        )

        assert state is not None
        assert state.execution_id == execution_id
        assert state.task_id == task.task_id
        assert state.session_id == task.session_id
        assert state.status is ExecutionStatus.COMPLETED

    finally:
        await application.stop()


@pytest.mark.asyncio
async def test_execution_failure_is_persisted(
    failing_application: AgentApplication,
) -> None:
    """
    When Agent execution fails, the logical Execution is persisted
    as FAILED.
    """

    application = failing_application

    await application.initialize()
    await application.start()

    try:
        task = TaskRequest(
            task_id="task-failed-001",
            user_input="test failing execution",
        )

        with pytest.raises(
            RuntimeError,
            match="test agent failure",
        ):
            await application.execute(
                task
            )

        states = application.execution_store._states

        assert len(states) == 1

        execution_id = next(iter(states))

        state = await application.execution_store.load(
            execution_id
        )

        assert state is not None
        assert state.execution_id == execution_id
        assert state.task_id == task.task_id
        assert state.status is ExecutionStatus.FAILED

    finally:
        await application.stop()


@pytest.mark.asyncio
async def test_execution_persistence_contains_durable_state_only(
    successful_application: AgentApplication,
) -> None:
    """
    Execution persistence stores ExecutionState rather than live
    runtime objects.
    """

    application = successful_application

    await application.initialize()
    await application.start()

    try:
        task = TaskRequest(
            task_id="task-isolation-001",
            user_input="test execution isolation",
        )

        await application.execute(
            task
        )

        states = application.execution_store._states

        assert len(states) == 1

        execution_id = next(iter(states))

        state = await application.execution_store.load(
            execution_id
        )

        assert state is not None

        assert hasattr(
            state,
            "execution_id",
        )

        assert hasattr(
            state,
            "status",
        )

        assert not hasattr(
            state,
            "runtime_context",
        )

        assert not hasattr(
            state,
            "execution_handle",
        )

    finally:
        await application.stop()