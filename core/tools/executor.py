from context.session_context import SessionContext
from core.tools import tool_event
from core.tools.registry import ToolRegistry
from core.tools.request import ToolRequest
from core.tools.result import ToolResult
from event.publisher import EventPublisher


class ToolExecutor:

    def __init__(self, registry: ToolRegistry, publisher: EventPublisher):
        self.registry = registry
        self._publisher = publisher

    async def execute(
            self,
            request: ToolRequest,
            context: SessionContext
    ) -> ToolResult:
        try:
            tool = self.registry.get(request.tool_name)

            result = await tool.execute(
                input=request.arguments,
                context=context
            )

            self._publish_tool_event(request, result)

            return result

        except Exception as e:

            result = ToolResult(
                success=False,
                output=None,
                error=str(e)
            )

            self._publish_tool_event(request, result)

            return result

    def _publish_tool_event(
            self,
            request: ToolRequest,
            result: ToolResult
    ):
        try:
            if result.success:
                event = tool_event.tool_executed(
                    tool_name=request.tool_name
                )
            else:
                event = tool_event.tool_failed(
                    tool_name=request.tool_name,
                    error=str(result.error) if result.error else ""
                )

            self._publisher.emit(event)

        except Exception:
            # Event 不允许影响主流程
            pass