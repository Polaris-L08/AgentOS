from reflection.reflection import Reflection


class MockCriticAgent:

    def __init__(
        self,
        reflection: Reflection
    ):
        self.call_count = 0

        self.observation_history = None

        self.reflection = reflection

    async def reflect(
        self,
        observations
    ) -> Reflection:

        self.call_count += 1

        self.observation_history = observations

        return self.reflection