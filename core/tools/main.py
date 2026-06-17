import asyncio

from core.context.session import SessionContext
from core.tools import registry, request
from core.tools.executor import ToolExecutor
from core.tools.fake_echo_tool import FakeEchoTool
from core.tools.registry import ToolRegistry
from core.tools.request import ToolRequest


async def main():
    registry = ToolRegistry()

    registry.register(FakeEchoTool())

    executor = ToolExecutor(registry)

    request = ToolRequest(
        tool_name="fake_echo",
        arguments={
            "input": "hello world"
        }
    )

    session0 = SessionContext()

    result = await executor.execute(request, session0)

    session1 = session0.apply_patch(result.patch)

    print(session0.state.scratchpad)
    print(session1.state.scratchpad)

asyncio.run(main())