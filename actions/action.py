from dataclasses import field, dataclass
from typing import Any


@dataclass(frozen=True)
class Action:
    pass


@dataclass(frozen=True)
class ToolAction(Action):

    tool_name: str

    arguments: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class FinishAction(Action):

    answer: str