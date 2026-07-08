from abc import ABC, abstractmethod

from models.action import Action
from actions.observation import Observation
from models.task import Task
from runtime.context.runtime_context import RuntimeContext


class BasePlanner(ABC):

    @abstractmethod
    async def plan(
        self,
        task: Task,
        context: RuntimeContext,
        observation: Observation | None
    ) -> Action:
        pass