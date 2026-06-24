import asyncio

from actions.action_executor import ActionExecutor
from agents.code_agent import CodeAgent
from core.task import Task
from planner.code_planner import CodePlanner
from planner.mock_planner import MockPlanner
from providers.mock_llm_provider import MockLLMProvider
from tools.tool_executor import ToolExecutor


async def test_agent_loop():

    # planner = MockPlanner()
    provider = MockLLMProvider()
    planner = CodePlanner(provider)

    executor = ActionExecutor(ToolExecutor())

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