import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.agents import AgentRegistry
from runtime.application.application import AgentApplication
from runtime.execution import Execution
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_handle import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    async def run(self, task, agent_execution_context):
        return f"processed: {task.user_input}"


def create_application() -> AgentApplication:
    trace_recorder = TraceRecorder()

    agent_runtime = AgentRuntime()
    execution_runtime = ExecutionRuntime(
        trace_recorder=trace_recorder
    )

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
        execution_runtime=execution_runtime,
        agent_registry=AgentRegistry([agent]),
    )


@pytest.mark.asyncio
async def test_application_invokes_agent_through_agent_runtime():
    application = create_application()

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


@pytest.mark.asyncio
async def test_application_resolves_agent_before_invocation():
    application = create_application()

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

    assert result.output == "processed: hello"


@pytest.mark.asyncio
async def test_unknown_agent_is_rejected():
    application = create_application()

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    with pytest.raises(KeyError, match="Agent not found"):
        await application.invoke_agent(
            agent_id="unknown-agent",
            task=task,
            execution_handle=execution,
        )


@pytest.mark.asyncio
async def test_invocation_requires_running_application():
    application = create_application()

    execution = application.execution_runtime.create_execution()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    with pytest.raises(RuntimeError):
        await application.invoke_agent(
            agent_id="agent-1",
            task=task,
            execution_handle=execution,
        )


@pytest.mark.asyncio
async def test_application_uses_execution_handle_runtime_context():
    application = create_application()

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    runtime_context = execution.runtime_context

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
    assert execution.runtime_context is runtime_context


@pytest.mark.asyncio
async def test_multiple_agents_can_be_invoked_in_same_execution():
    application = create_application()

    second_agent = MockAgent(
        identity=AgentIdentity(
            agent_id="agent-2",
            agent_type="mock",
            name="Second Mock Agent",
        )
    )

    application.add_agent(second_agent)

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    task_1 = TaskRequest(
        task_id="task-1",
        user_input="first",
    )

    task_2 = TaskRequest(
        task_id="task-2",
        user_input="second",
    )

    result_1 = await application.invoke_agent(
        agent_id="agent-1",
        task=task_1,
        execution_handle=execution,
    )

    result_2 = await application.invoke_agent(
        agent_id="agent-2",
        task=task_2,
        execution_handle=execution,
    )

    assert result_1.output == "processed: first"
    assert result_2.output == "processed: second"


@pytest.mark.asyncio
async def test_agent_invocations_share_same_execution_context():
    application = create_application()

    second_agent = MockAgent(
        identity=AgentIdentity(
            agent_id="agent-2",
            agent_type="mock",
            name="Second Mock Agent",
        )
    )

    application.add_agent(second_agent)

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    task_1 = TaskRequest(
        task_id="task-1",
        user_input="first",
    )

    task_2 = TaskRequest(
        task_id="task-2",
        user_input="second",
    )

    await application.invoke_agent(
        agent_id="agent-1",
        task=task_1,
        execution_handle=execution,
    )

    await application.invoke_agent(
        agent_id="agent-2",
        task=task_2,
        execution_handle=execution,
    )

    assert execution.runtime_context.trace.trace.end_time is None


@pytest.mark.asyncio
async def test_application_does_not_close_execution_after_agent_invocation():
    application = create_application()

    await application.initialize()
    await application.start()

    execution = application.execution_runtime.create_execution()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    await application.invoke_agent(
        agent_id="agent-1",
        task=task,
        execution_handle=execution,
    )

    assert execution.closed is False


@pytest.mark.asyncio
async def test_execution_can_be_closed_after_agent_invocation():
    application = create_application()

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )

    execution = Execution(
        execution_id="execution-id",
        task_id=task.task_id,
        session_id=task.session_id,
    )
    execution_handle = application.execution_runtime.create_execution(execution)

    await application.invoke_agent(
        agent_id="agent-1",
        task=task,
        execution_handle=execution_handle,
    )

    await execution_handle.close()

    assert execution_handle.closed is True
    assert execution_handle.runtime_context.trace.trace.end_time is not None


@pytest.mark.asyncio
async def test_application_invoke_agent_delegates_to_agent_runtime():
    application = create_application()

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-1",
        user_input="hello",
    )
    execution = Execution(
        execution_id="execution-id",
        task_id=task.task_id,
        session_id=task.session_id,
    )

    execution_handle = application.execution_runtime.create_execution(execution)

    original_execute = application.agent_runtime.execute

    calls = []

    async def recording_execute(
        *,
        agent,
        task,
        runtime_context,
        agent_execution_context=None,
    ):
        calls.append(
            {
                "agent": agent,
                "task": task,
                "runtime_context": runtime_context,
                "agent_execution_context": (
                    agent_execution_context
                ),
            }
        )

        return await original_execute(
            agent=agent,
            task=task,
            runtime_context=runtime_context,
            agent_execution_context=agent_execution_context,
        )

    application.agent_runtime.execute = recording_execute

    result = await application.invoke_agent(
        agent_id="agent-1",
        task=task,
        execution_handle=execution_handle,
    )

    assert result.success is True

    assert len(calls) == 1
    assert calls[0]["agent"] is application.get_agent(
        "agent-1"
    )
    assert calls[0]["task"] is task
    assert (
        calls[0]["runtime_context"]
        is execution_handle.runtime_context
    )