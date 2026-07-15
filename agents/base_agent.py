from abc import ABC, abstractmethod

from runtime.component import RuntimeComponent
from runtime.context.runtime_context import RuntimeContext


class BaseAgent(RuntimeComponent, ABC):
    def __init__(self, name: str, middleware_chain = None):
        super().__init__(middleware_chain)
        self.name = name

    @abstractmethod
    async def run(
            self,
            task,
            runtime_context: RuntimeContext
    ):
        """
        Agent execution entry.

        Agent decides:
        - planning
        - action generation
        - reflection

        Runtime handles:
        - middleware
        - tracing
        - checkpoint
        """
        pass