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
from tests.mocks.mock_planner import MockPlanner
from tests.mocks.mock_tool import MockTool
from tools.executor import ToolExecutor
from tools.registry import ToolRegistry

@pytest.mark.asyncio
async def test_full_runtime_execution_with_trace():
    #
    # Given
    #
    registry = ToolRegistry()

    registry.register(MockTool())

    event_bus = EventBus()

    middleware_chain = MiddlewareChain(
        [
            TracingMiddleware()
        ]
    )

    executor = ToolExecutor(
        registry=registry,
        publisher=event_bus,
        middleware_chain=middleware_chain
    )

    planner = MockPlanner(
        [
            ToolAction(tool_name="mock_tool", arguments={}),
            FinishAction(answer="done")
        ]
    )

    critic = MockCriticAgent()

    # 创建RuntimeContext
    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    runtime_context = (
        execution_runtime.create_context(
            ContextState()
        )
    )

    task = TaskRequest(
        task_id="test-1",
        user_input="trace executor"
    )

    agent = CodeAgent(planner, executor, critic, middleware_chain=middleware_chain)

    #
    # When
    #

    result = await agent.run(
        task,
        runtime_context
    )

    await execution_runtime.close(runtime_context)

    #
    # Then
    #
    assert result.success is True

    assert result.answer == "done"

    #
    # Loop state
    #

    loop = runtime_context.loop

    assert loop.step_count == 1

    assert len(loop.observation_history) == 1

    #
    # trace
    #

    trace = runtime_context.trace.trace

    assert trace.span_count >= 3

    assert trace.root_span_id is not None

    assert trace.duration_ms is not None

    #
    # formatter
    #

    report = TraceFormatter().format(trace)

    assert "agent.run" in report

    assert "planner.plan" in report

    assert "tool.execute" in report

    print(report)