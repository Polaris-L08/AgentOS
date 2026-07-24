from copy import deepcopy
from dataclasses import field
from typing import Optional

from pydantic.dataclasses import dataclass

from models.action import Action
from actions.observation import Observation


@dataclass
class LoopState:
    step_count: int = 0

    # finished: bool = False

    last_action: Optional[Action] = None

    # last_observation: Optional[Observation] = None

    observation_history: list[Observation] = field(default_factory=list)

    reflection_count: int = 0

    def copy(self) -> "LoopState":
        """
        Create isolated loop state.

        Used when one Agent invokes another Agent.

        Child Agent must not modify parent's execution loop.
        """

        return LoopState(
            step_count=self.step_count,
            last_action=deepcopy(self.last_action),
            observation_history=deepcopy(self.observation_history),
            reflection_count=self.reflection_count
        )