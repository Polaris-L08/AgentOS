import pytest

from actions.observation import Observation
from agents.code_agent import CodeAgent
from models.action import FinishAction, ToolAction
from models.task import Task
from models.task_request import TaskRequest
from reflection.reflection import Reflection
from runtime.checkpoint import CheckpointStore, MemoryCheckpointStore
from runtime.context.context_state import ContextState
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.tracing_middleware import TracingMiddleware
from tests.mocks.mock_action_executor import MockActionExecutor
from tests.mocks.mock_critic_agent import MockCriticAgent
from tests.mocks.mock_planner import MockPlanner


@pytest.fixture
def tracing_middleware_chain():

    return MiddlewareChain(
        [TracingMiddleware()]
    )

@pytest.mark.asyncio
async def test_planner_should_create_trace_span(tracing_middleware_chain):
    planner = MockPlanner(
        [FinishAction(
            answer="done"
        )]
    )

    executor = MockActionExecutor([])

    critic = MockCriticAgent(
        Reflection(
            summary="",
            suggestions=[]
        )
    )

    checkpoint_store = MemoryCheckpointStore()

    agent = CodeAgent(
        planner,
        executor,
        critic,
        checkpoint_store=checkpoint_store,
        middleware_chain=tracing_middleware_chain
    )

    result = await agent.run(
        TaskRequest(
            task_id="1",
            user_input="trace planner"
        ),
        ContextState()
    )

    assert result.success is True

    trace = agent.last_runtime_context.trace.trace

    spans = trace.all_spans()

    assert len(spans) == 1

    span = spans[0]

    assert span.name == "planner.plan"

    assert span.status.value == "success"

@pytest.mark.asyncio
async def test_executor_should_create_trace_span(tracing_middleware_chain):
    planner = MockPlanner(
        [
            ToolAction(tool_name="run_test",arguments={}),
            FinishAction(answer="done")
        ]
    )

    executor = MockActionExecutor(
        [
            Observation(success=True, content="ok")
        ]
    )

    critic = MockCriticAgent(
        Reflection(
            summary="",
            suggestions=[]
        )
    )

    agent = CodeAgent(
        planner,
        executor,
        critic,
        middleware_chain=tracing_middleware_chain
    )

    result = await agent.run(
        TaskRequest(
            task_id="1",
            user_input="trace executor"
        ),
        ContextState()
    )

    assert result.success is True

    spans = (
        agent
        .last_runtime_context
        .trace
        .trace
        .all_spans()
    )

    names = [
        span.name
        for span in spans
    ]

    assert "planner.plan" in names

    assert "tool.execute" in names

@pytest.mark.asyncio
async def test_reflection_should_create_trace_span(
    tracing_middleware_chain,
):

    planner = MockPlanner(
        [
            ToolAction(
                tool_name="run_test",
                arguments={}
            ),
            FinishAction(
                answer="fixed"
            )
        ]
    )


    executor = MockActionExecutor(
        [
            Observation(
                success=False,
                content="failed"
            )
        ]
    )


    critic = MockCriticAgent(
        Reflection(
            summary="fix",
            suggestions=[]
        )
    )


    agent = CodeAgent(
        planner,
        executor,
        critic,
        middleware_chain=tracing_middleware_chain,
    )


    result = await agent.run(
        TaskRequest(
            task_id="1",
            user_input="trace reflection",
        ),
        ContextState()
    )


    assert result.success is True


    names = [
        span.name
        for span in (
            agent
            .last_runtime_context
            .trace
            .trace
            .all_spans()
        )
    ]


    assert "reflection.reflect" in names