import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.application import AgentApplication
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class RecordingAgent(BaseAgent):
    def __init__(self, identity):
        super().__init__(identity=identity)
        self.tasks: list[TaskRequest] = []

    async def run(
        self,
        task,
        agent_execution_context,
    ):
        self.tasks.append(task)

        return f"processed: {task.user_input}"


def create_application(
    agent=None,
) -> AgentApplication:
    if agent is None:
        agent = RecordingAgent(
            identity=AgentIdentity(
                agent_id="agent-1",
                agent_type="recording",
                name="Recording Agent",
            )
        )

    return AgentApplication(
        application_id="app-1",
        name="Test Application",
        agent_runtime=AgentRuntime(),
        execution_runtime=ExecutionRuntime(
            trace_recorder=TraceRecorder(),
        ),
        agents=[agent],
    )


@pytest.mark.asyncio
async def test_task_request_session_id_is_optional():
    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    assert task.session_id is None


@pytest.mark.asyncio
async def test_stateless_execution_remains_supported():
    application = create_application()

    await application.initialize()
    await application.start()

    result = await application.execute(
        TaskRequest(
            task_id="task-1",
            user_input="hello",
        )
    )

    assert result.success is True
    assert result.answer == "processed: hello"

    await application.stop()


@pytest.mark.asyncio
async def test_session_based_execution_is_supported():
    application = create_application()

    await application.initialize()
    await application.start()

    session = application.create_session()

    result = await application.execute(
        TaskRequest(
            task_id="task-1",
            user_input="hello",
            session_id=session.session_id,
        )
    )

    assert result.success is True
    assert result.answer == "processed: hello"

    await application.stop()


@pytest.mark.asyncio
async def test_task_session_must_belong_to_application():
    application = create_application()
    other_application = create_application()

    await application.initialize()
    await application.start()

    await other_application.initialize()
    await other_application.start()

    session = other_application.create_session()

    with pytest.raises(
        KeyError,
        match=f"Session not found: {session.session_id}",
    ):
        await application.execute(
            TaskRequest(
                task_id="task-1",
                user_input="hello",
                session_id=session.session_id,
            )
        )

    await application.stop()
    await other_application.stop()


@pytest.mark.asyncio
async def test_unknown_task_session_fails_before_agent_execution():
    agent = RecordingAgent(
        identity=AgentIdentity(
            agent_id="agent-1",
            agent_type="recording",
            name="Recording Agent",
        )
    )

    application = create_application(agent)

    await application.initialize()
    await application.start()

    with pytest.raises(
        KeyError,
        match="Session not found: unknown-session",
    ):
        await application.execute(
            TaskRequest(
                task_id="task-1",
                user_input="hello",
                session_id="unknown-session",
            )
        )

    assert agent.tasks == []

    await application.stop()


@pytest.mark.asyncio
async def test_same_session_can_be_used_by_multiple_executions():
    application = create_application()

    await application.initialize()
    await application.start()

    session = application.create_session()

    result1 = await application.execute(
        TaskRequest(
            task_id="task-1",
            user_input="hello",
            session_id=session.session_id,
        )
    )

    result2 = await application.execute(
        TaskRequest(
            task_id="task-2",
            user_input="world",
            session_id=session.session_id,
        )
    )

    assert result1.success is True
    assert result2.success is True

    assert result1.answer == "processed: hello"
    assert result2.answer == "processed: world"

    await application.stop()


@pytest.mark.asyncio
async def test_session_does_not_become_runtime_context_state():
    application = create_application()

    await application.initialize()
    await application.start()

    session = application.create_session()

    execution = application.execution_runtime.create_execution()

    try:
        assert execution.runtime_context.runtime_id

        assert not hasattr(
            execution.runtime_context,
            "session_id",
        )

        assert (
            session.session_id
            != execution.runtime_context.runtime_id
        )
    finally:
        await execution.close()
        await application.stop()