from actions.action import Action


class MockPlanner:

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