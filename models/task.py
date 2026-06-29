from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    id: str

    objective: str

    metadata: dict[str, Any] = field(default_factory=dict)