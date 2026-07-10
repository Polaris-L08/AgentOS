from typing import Any

from runtime.context.context_state import ContextState
from tools.base import AbstractTool
from tools.result import ToolResult


class MockTool(AbstractTool):

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "Mock Tool"

    async def execute(
            self,
            input: Any,
            context: ContextState
    ) -> ToolResult:
        return ToolResult(
            success=True,
            output="tool finished"
        )