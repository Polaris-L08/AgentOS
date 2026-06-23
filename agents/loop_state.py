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