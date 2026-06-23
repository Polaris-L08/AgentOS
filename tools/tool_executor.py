from tools.tool_request import ToolRequest
from tools.tool_result import ToolResult


class ToolExecutor:

    async def execute(selfself, request: ToolRequest) -> ToolResult:

        if request.tool_name == "echo":
            return ToolResult(
                success=True,
                output=request.arguments.get("msg", "")
            )

        return ToolResult(
            success=False,
            output="unknown tool"
        )