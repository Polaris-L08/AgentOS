from actions.action import ToolAction, FinishAction
from actions.observation import Observation
from tools.tool_executor import ToolExecutor
from tools.tool_request import ToolRequest


class ActionExecutor:

    def __init__(self, tool_executor: ToolExecutor):
        self.tool_executor = tool_executor

    async def execute(self, action) -> Observation:

        if isinstance(action, ToolAction):

            request = ToolRequest(
                tool_name=action.tool_name,
                arguments=action.arguments
            )

            result = await self.tool_executor.execute(request)

            return Observation(
                success=result.success,
                content=result.output,
                metadata=result.metadata or {}
            )

        elif isinstance(action, FinishAction):
            return Observation(
                success=True,
                content=action.answer
            )

        return Observation(
            success=False,
            content="invalid action"
        )