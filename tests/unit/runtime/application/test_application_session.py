import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from runtime.application.application import AgentApplication
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    async def run(
        self,
        task,
        agent_execution_context,
    ):
        return "mock result"


def create_application() -> AgentApplication:
    agent = MockAgent(
        identity=AgentIdentity(
            agent_id="mock-agent",
            agent_type="mock",
            name="Mock Agent",
        )
    )

    return AgentApplication(
        application_id="test-application",
        name="Test Application",
        agent_runtime=AgentRuntime(),
        execution_runtime=ExecutionRuntime(
            trace_recorder=TraceRecorder()
        ),
        agents=[agent],
    )


@pytest.mark.asyncio
async def test_application_creates_session_when_running():
    application = create_application()

    await application.initialize()
    await application.start()

    session = application.create_session()

    assert session.session_id
    assert application.has_session(
        session.session_id
    )


@pytest.mark.asyncio
async def test_application_can_get_owned_session():
    application = create_application()

    await application.initialize()
    await application.start()

    session = application.create_session()

    result = application.get_session(
        session.session_id
    )

    assert result is session


@pytest.mark.asyncio
async def test_application_can_delete_owned_session():
    application = create_application()

    await application.initialize()
    await application.start()

    session = application.create_session()

    application.delete_session(
        session.session_id
    )

    assert application.has_session(
        session.session_id
    ) is False


def test_create_session_requires_running_application():
    application = create_application()

    with pytest.raises(ApplicationLifecycleError):
        application.create_session()


@pytest.mark.asyncio
async def test_create_session_requires_running_application_after_initialize():
    application = create_application()

    await application.initialize()

    with pytest.raises(ApplicationLifecycleError):
        application.create_session()


@pytest.mark.asyncio
async def test_create_session_fails_after_application_stops():
    application = create_application()

    await application.initialize()
    await application.start()
    await application.stop()

    with pytest.raises(ApplicationLifecycleError):
        application.create_session()


def test_get_session_requires_running_application():
    application = create_application()

    with pytest.raises(ApplicationLifecycleError):
        application.get_session("unknown")


@pytest.mark.asyncio
async def test_get_unknown_session_raises_key_error():
    application = create_application()

    await application.initialize()
    await application.start()

    with pytest.raises(KeyError, match="Session not found"):
        application.get_session("unknown-session")


@pytest.mark.asyncio
async def test_application_owns_its_sessions():
    application_1 = create_application()
    application_2 = create_application()

    await application_1.initialize()
    await application_1.start()

    await application_2.initialize()
    await application_2.start()

    session = application_1.create_session()

    assert application_1.has_session(
        session.session_id
    ) is True

    assert application_2.has_session(
        session.session_id
    ) is False


@pytest.mark.asyncio
async def test_application_can_have_multiple_sessions():
    application = create_application()

    await application.initialize()
    await application.start()

    session_1 = application.create_session()
    session_2 = application.create_session()

    assert session_1.session_id != session_2.session_id

    assert application.has_session(
        session_1.session_id
    ) is True

    assert application.has_session(
        session_2.session_id
    ) is True


@pytest.mark.asyncio
async def test_session_metadata_is_preserved():
    application = create_application()

    await application.initialize()
    await application.start()

    session = application.create_session(
        metadata={
            "channel": "api",
            "client": "test",
        }
    )

    assert session.metadata == {
        "channel": "api",
        "client": "test",
    }


@pytest.mark.asyncio
async def test_application_uses_injected_session_manager():
    from runtime.session.session_manager import SessionManager

    session_manager = SessionManager()

    application = AgentApplication(
        application_id="test-application",
        name="Test Application",
        agent_runtime=AgentRuntime(),
        execution_runtime=ExecutionRuntime(
            trace_recorder=TraceRecorder()
        ),
        session_manager=session_manager,
    )

    await application.initialize()
    await application.start()

    session = application.create_session()

    assert application.session_manager is session_manager

    assert session_manager.has_session(
        session.session_id
    )