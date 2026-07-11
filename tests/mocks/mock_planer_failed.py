from models.action import Action
from planner.base_planner import BasePlanner


class MockPlannerException(BasePlanner):
    def __init__(
            self,
            exception: Exception
    ):
        self._exception = exception
        self._index = 0

    async def plan(
            self,
            task,
            context,
            observation
    ) -> Action | None:
        raise self._exception