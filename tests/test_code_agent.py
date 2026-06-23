import asyncio

from actions.mock_executor import MockExecutor
from agents.code_agent import CodeAgent
from core.agent_context import AgentContext
from core.task import Task
from planner.mock_planner import MockPlanner


async def test_agent_loop():

    planner = MockPlanner()

    executor = MockExecutor()

    agent = CodeAgent(
        planner,
        executor
    )

    task = Task(
        id="1",
        objective="say hello"
    )

    result = await agent.run(
        task,
        context={}
    )

    print(result)
    assert result.success

    assert result.answer == "done"

asyncio.run(test_agent_loop())