from abc import ABC, abstractmethod

from actions.action import Action
from actions.observation import Observation
from core.agent_context import AgentContext
from core.task import Task


class BasePlanner(ABC):

    @abstractmethod
    async def plan(
        self,
        task: Task,
        context: AgentContext,
        observation: Observation | None
    ) -> Action:
        pass