from dataclasses import field, dataclass
from typing import Any


@dataclass(frozen=True)
class TaskResult:
    success: bool

    answer: str

    metadata: dict[str, Any] = field(default_factory=dict)