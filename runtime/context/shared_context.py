from typing import Any

from pydantic import BaseModel, Field


class SharedContext(BaseModel):

    data: dict[str, Any] = Field(default_factory=dict)

    def set(self, key: str, value: Any):
        self.data[key] = value

    def get(self, key: str, default = None):
        return self.data.get(key, default)