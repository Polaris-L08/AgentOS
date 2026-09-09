import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from models.task_result import TaskResult
from runtime.application import AgentApplication
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    async def run(
        self,
        task: TaskRequest,
        agent_execution_context,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output=f"processed: {task.user_input}",
        )


class FailingAgent(BaseAgent):
    async def run(
        self,
        task: TaskRequest,
        agent_execution_context,
    ) -> AgentResult:
        raise RuntimeError("agent execution failed")


def create_agent(
    agent_id: str = "agent-001",
) -> MockAgent:
    return MockAgent(
        identity=AgentIdentity(
            agent_id=agent_id,
            agent_type="mock",
            name=agent_id,
        )
    )


def create_application(
    agents: list[BaseAgent] | None = None,
) -> AgentApplication:
    return AgentApplication(
        application_id="app-001",
        name="Test Application",
        agent_runtime=AgentRuntime(),
        execution_runtime=ExecutionRuntime(
            trace_recorder=TraceRecorder()
        ),
        agents=agents,
    )


@pytest.mark.asyncio
async def test_application_execute_requires_running_state():
    application = create_application(
        agents=[create_agent()]
    )

    task = TaskRequest(
        task_id="task-001",
        user_input="hello",
    )

    with pytest.raises(ApplicationLifecycleError):
        await application.execute(task)


@pytest.mark.asyncio
async def test_application_execute_returns_task_result():
    application = create_application(
        agents=[create_agent()]
    )

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-001",
        user_input="hello",
    )

    result = await application.execute(task)

    assert isinstance(result, TaskResult)
    assert result.success is True
    assert result.answer == "processed: hello"

    await application.stop()


@pytest.mark.asyncio
async def test_application_execute_preserves_agent_metadata():
    application = create_application(
        agents=[create_agent()]
    )

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-001",
        user_input="hello",
    )

    result = await application.execute(task)

    assert result.metadata["agent_id"] == "agent-001"
    assert result.metadata["agent_type"] == "mock"

    await application.stop()


@pytest.mark.asyncio
async def test_each_execute_creates_independent_runtime_contexts():
    application = create_application(
        agents=[create_agent()]
    )

    await application.initialize()
    await application.start()

    task1 = TaskRequest(
        task_id="task-001",
        user_input="hello",
    )

    task2 = TaskRequest(
        task_id="task-002",
        user_input="world",
    )

    result1 = await application.execute(task1)
    result2 = await application.execute(task2)

    assert result1.answer == "processed: hello"
    assert result2.answer == "processed: world"

    await application.stop()


@pytest.mark.asyncio
async def test_application_execute_propagates_agent_exception():
    agent = FailingAgent(
        identity=AgentIdentity(
            agent_id="failing-agent",
            agent_type="failing",
            name="Failing Agent",
        )
    )

    application = create_application(
        agents=[agent]
    )

    await application.initialize()
    await application.start()

    task = TaskRequest(
        task_id="task-001",
        user_input="hello",
    )

    with pytest.raises(
        RuntimeError,
        match="agent execution failed",
    ):
        await application.execute(task)

    assert application.is_running is True

    await application.stop()