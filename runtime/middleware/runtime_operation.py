import uuid
from dataclasses import dataclass, field
from typing import Any

@dataclass(slots=True)
class RuntimeOperation:
    name: str
    component: str
    metadata: dict[str, Any]
    operation_id: str = field(default_factory=lambda : str(uuid.uuid4()))