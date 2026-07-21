from dataclasses import dataclass, field
from typing import Any


@dataclass
class SharedContext:

    data: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any):
        self.data[key] = value

    def get(self, key: str, default = None):
        return self.data.get(key, default)