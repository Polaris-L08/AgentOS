from runtime.events.event import Event


# class ToolEvents:
#
#     @staticmethod
#     def executed(request: ToolRequest, result: ToolResult, trace_id: str) -> Event:
#
#         return Event(
#             type="tool.executed",
#             source="tool_executor",
#             trace_id=trace_id,
#             payload={
#                 "tool_name": request.tool_name,
#                 "success": result.success
#             }
#         )

TOOL_EXECUTED = "tool.executed"
TOOL_FAILED = "tool.failed"

def tool_executed(*, tool_name: str) -> Event:
    return Event(
        type=TOOL_EXECUTED,
        source="tool_executor",
        payload={
            "tool_name": tool_name
        }
    )

def tool_failed(*, tool_name: str, error: str) -> Event:
    return Event(
        type=TOOL_FAILED,
        source="tool_executor",
        payload={
            "tool_name": tool_name,
            "error": error
        }
    )