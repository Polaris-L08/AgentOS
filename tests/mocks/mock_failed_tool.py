from typing import Any

from runtime.context.context_state import ContextState
from tools.base import AbstractTool
from tools.result import ToolResult


class MockFailedTool(AbstractTool):

    @property
    def name(self) -> str:
        return "failed_tool"

    @property
    def description(self) -> str:
        return "failed tool"

    async def execute(
            self,
            input: Any,
            context: ContextState
    ) -> ToolResult:
        raise RuntimeError(
            "mock tool failed"
        )