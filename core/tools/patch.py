from typing import Any
from pydantic import BaseModel, Field


class ContextPatch(BaseModel):
    """
    Describe how a tool intends to mutate Context
    """

    updates: dict[str, Any] = Field(default_factory=dict)