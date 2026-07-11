from models.action import Action
from planner.base_planner import BasePlanner


class MockPlanner(BasePlanner):

    def __init__(
        self,
        actions: list[Action]
    ):
        self._actions = actions
        self._index = 0

    async def plan(
        self,
        task,
        context,
        observation
    ) -> Action:

        action = self._actions[self._index]

        self._index += 1

        return action