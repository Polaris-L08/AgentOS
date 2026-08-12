from runtime.component.runtime_component import RuntimeComponent
from runtime.context import AgentExecutionContext
from runtime.context.runtime_context import RuntimeContext
from runtime.middleware.middleware_chain import MiddlewareChain
from tools import tool_event
from tools.exceptions import ToolExecutionError
from tools.registry import ToolRegistry
from tools.request import ToolRequest
from tools.result import ToolResult
from runtime.events.publisher import EventPublisher
from runtime.middleware.runtime_operation import RuntimeOperation


class ToolExecutor(RuntimeComponent):

    def __init__(self, registry: ToolRegistry, publisher: EventPublisher, middleware_chain: MiddlewareChain | None = None):
        super().__init__(middleware_chain)
        self.registry = registry
        self._publisher = publisher

    async def execute(
            self,
            request: ToolRequest,
            context: AgentExecutionContext
    ) -> ToolResult:
        return await self.invoke(
            RuntimeOperation(
                name="tool.execute",
                component="tool_executor",
                metadata={
                    "tool": request.tool_name
                }
            ),
            context.runtime_context,
            self._execute,
            request,
            context
        )

    async def _execute(self, request: ToolRequest, agent_context: AgentExecutionContext):
        context_state = agent_context.state

        try:
            tool = self.registry.get(request.tool_name)
            result = await tool.execute(input=request.arguments, context_state=context_state)

        except ToolExecutionError as e:
            result = ToolResult(
                success=False,
                output=None,
                error=str(e)
            )
        except Exception as e:
            raise

        self._publish_tool_event(request, result, agent_context.runtime_context)

        return result

    def _publish_tool_event(
            self,
            request: ToolRequest,
            result: ToolResult,
            runtime_context: RuntimeContext
    ):
        try:
            if result.success:
                event = tool_event.tool_executed(
                    tool_name=request.tool_name,
                    trace_id=runtime_context.trace.trace.trace_id,
                    span_id=runtime_context.trace.current_span_id
                )
            else:
                event = tool_event.tool_failed(
                    tool_name=request.tool_name,
                    error=str(result.error) if result.error else "",
                    trace_id=runtime_context.trace.trace.trace_id,
                    span_id=runtime_context.trace.current_span_id
                )

            self._publisher.emit(event)

        except Exception:
            # Event 不允许影响主流程
            pass