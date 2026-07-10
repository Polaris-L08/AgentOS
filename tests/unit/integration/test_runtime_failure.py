import pytest

from agents.code_agent import CodeAgent
from models.action import ToolAction, FinishAction
from models.task_request import TaskRequest
from runtime.context.context_state import ContextState
from runtime.events.event_bus import EventBus
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.tracing_middleware import TracingMiddleware
from runtime.tracing.trace_formatter import TraceFormatter
from runtime.tracing.trace_recorder import TraceRecorder
from tests.mocks.mock_critic_agent import MockCriticAgent
from tests.mocks.mock_failed_tool import MockFailedTool
from tests.mocks.mock_planner import MockPlanner
from tools.executor import ToolExecutor
from tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_runtime_failure_should_record_error_trace():
    #
    # Given
    #
    registry = ToolRegistry()

    registry.register(MockFailedTool())

    event_bus = EventBus()

    middleware_chain = MiddlewareChain(
        [
            TracingMiddleware()
        ]
    )

    executor = ToolExecutor(registry, event_bus, middleware_chain)

    planner = MockPlanner(
        [
            ToolAction(tool_name="failed_tool", arguments={}),
            FinishAction(answer="failed handled")
        ]
    )

    critic = MockCriticAgent()

    agent = CodeAgent(planner, executor, critic)

    execution_runtime = ExecutionRuntime(trace_recorder=TraceRecorder())

    runtime_context = execution_runtime.create_context(ContextState())

    task = TaskRequest(
        task_id="failure-test",
        user_input="test failure"
    )

    #
    # When
    #
    result = await agent.run(task, runtime_context)

    await execution_runtime.close(runtime_context)

    #
    # Then
    #
    assert result.success is True

    trace = runtime_context.trace.trace

    report = TraceFormatter().format(trace)

    print(report)

    #
    # verify error span
    #

    failed_span = [
        span
        for span in trace.all_spans()
        if span.name == "tool.execute"
    ][0]

    assert (
            failed_span.status.name
            ==
            "ERROR"
    )


