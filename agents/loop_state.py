from dataclasses import field
from typing import Optional

from pydantic.dataclasses import dataclass

from actions.action import Action
from actions.observation import Observation


@dataclass
class LoopState:
    step_count: int = 0

    finished: bool = False

    last_action: Optional[Action] = None

    last_observation: Optional[Observation] = None

    observation_history: list[Observation] = field(default_factory=list)

    reflection_count: int = 0