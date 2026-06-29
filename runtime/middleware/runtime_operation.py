from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class RuntimeOperation:
    name: str
    component: str
    metadata: dict[str, Any]