from abc import ABC, abstractmethod

from models.action import Action
from actions.observation import Observation
from runtime.loop.agent_context import AgentContext
from models.task import Task


class BasePlanner(ABC):

    @abstractmethod
    async def plan(
        self,
        task: Task,
        context: AgentContext,
        observation: Observation | None
    ) -> Action:
        pass