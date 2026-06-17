from typing import Any

from core.context.session import SessionContext
from core.tools.base import AbstractTool
from core.tools.patch import ContextPatch
from core.tools.result import ToolResult


class FakeEchoTool(AbstractTool):
    """测试用
        示例Tool
    """
    @property
    def name(self) -> str:
        return "fake_echo"

    @property
    def description(self) -> str:
        return "echo input"

    async def execute(
            self,
            input: str,
            context: SessionContext
    ) -> ToolResult:

        previous = context.state.scratchpad

        patch = ContextPatch(
            updates={
                "scratchpad": previous + "\n" + str(input)
            }
        )

        return ToolResult(
            success=True,
            output=input,
            patch=patch
        )