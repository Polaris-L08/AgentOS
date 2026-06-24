import asyncio

import pytest

from actions.action import FinishAction, ToolAction
from actions.observation import Observation
from agents.code_agent import CodeAgent
from context.context_state import ContextState
from core.task import Task
from reflection.reflection import Reflection
from tests.mocks.mock_action_executor import MockActionExecutor
from tests.mocks.mock_critic_agent import MockCriticAgent
from tests.mocks.mock_planner import MockPlanner


@pytest.mark.asyncio
async def test_finish_action_should_not_trigger_reflection():

    planner = MockPlanner(
        [
            FinishAction(
                answer="done"
            )
        ]
    )

    executor = MockActionExecutor([])

    critic = MockCriticAgent(
        Reflection(
            summary="",
            suggestions=[]
        )
    )

    agent = CodeAgent(
        planner,
        executor,
        critic
    )
    context_state = ContextState()

    result = await agent.run(
        Task(
            id="1",
            objective="test",
            metadata={}
        ),
        context_state
    )

    assert result.success is True

    assert critic.call_count == 0

@pytest.mark.asyncio
async def test_reflect_once_then_finish():

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
                content="AssertionError"
            )
        ]
    )

    critic = MockCriticAgent(
        Reflection(
            summary="boundary error",
            suggestions=[
                "check index"
            ]
        )
    )

    context = ContextState()

    agent = CodeAgent(
        planner,
        executor,
        critic
    )

    result = await agent.run(
        Task(
            id="1",
            objective="quicksort",
            metadata={}
        ),
        context
    )

    assert result.success is True

    assert critic.call_count == 1

    assert len(
        context.reflections.reflections
    ) == 1

    assert (
        context
        .reflections
        .reflections[0]
        .summary
        == "boundary error"
    )