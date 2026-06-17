from core.context.session import SessionContext
from core.tools.registry import ToolRegistry
from core.tools.request import ToolRequest
from core.tools.result import ToolResult


class ToolExecutor:

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute(
            self,
            request: ToolRequest,
            context: SessionContext
    ) -> ToolResult:
        try:
            tool = self.registry.get(request.tool_name)

            return await tool.execute(
                input=request.arguments,
                context=context
            )

        except Exception as e:

            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )
