from runtime.context import ContextState
from tools import tool_event
from tools.registry import ToolRegistry
from tools.request import ToolRequest
from tools.result import ToolResult
from runtime.events.publisher import EventPublisher
from runtime.middleware import MiddlewareChain
from runtime.middleware.runtime_operation import RuntimeOperation


class ToolExecutor:

    def __init__(self, registry: ToolRegistry, publisher: EventPublisher, middleware_chain: MiddlewareChain | None = None):
        self.registry = registry
        self._publisher = publisher
        self._middleware_chain = middleware_chain

    async def execute(
            self,
            request: ToolRequest,
            context: ContextState
    ) -> ToolResult:
        operation = RuntimeOperation(
            name="execute",
            component="tool_executor",
            metadata={
                "tool": request.tool_name
            }
        )

        await self._middleware_chain.before(operation, context)

        result = None

        try:
            tool = self.registry.get(request.tool_name)

            result = await tool.execute(
                input=request.arguments,
                context=context
            )

            self._publish_tool_event(request, result)

            await self._middleware_chain.after(operation, context, result)

        except Exception as e:

            result = ToolResult(
                success=False,
                output=None,
                error=str(e)
            )

            self._publish_tool_event(request, result)

            await self._middleware_chain.on_error(operation, context, error=e)

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