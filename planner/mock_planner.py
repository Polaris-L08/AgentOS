from actions.action import Action, ToolAction, FinishAction
from planner.base_planner import BasePlanner


class MockPlanner(BasePlanner):

    def __init__(self):

        self.call_count = 0

    async def plan(
        self,
        task,
        context,
        observation
    ) -> Action:

        self.call_count += 1

        if self.call_count == 1:

            return ToolAction(
                tool_name="echo",
                arguments={
                    "message":"hello"
                }
            )

        return FinishAction(
            answer="done"
        )