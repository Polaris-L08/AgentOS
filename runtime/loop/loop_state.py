from copy import deepcopy

from typing import Optional

from pydantic import BaseModel, Field

from actions.observation import Observation
from models.action import Action


class LoopState(BaseModel):
    step_count: int = 0

    # finished: bool = False

    last_action: Optional[Action] = None

    # last_observation: Optional[Observation] = None

    observation_history: list[Observation] = Field(default_factory=list)

    reflection_count: int = 0

    def copy(self) -> "LoopState":
        """
        Create an isolated loop state copy.
        """

        return LoopState(
            step_count=self.step_count,
            last_action=deepcopy(self.last_action),
            observation_history=deepcopy(self.observation_history),
            reflection_count=self.reflection_count
        )