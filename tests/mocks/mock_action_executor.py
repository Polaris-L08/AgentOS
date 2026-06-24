from actions.observation import Observation


class MockActionExecutor:

    def __init__(
        self,
        observations: list[Observation]
    ):
        self._observations = observations
        self._index = 0

    async def execute(
        self,
        action
    ) -> Observation:

        observation = self._observations[self._index]

        self._index += 1

        return observation