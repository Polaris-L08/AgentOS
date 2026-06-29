from typing import Any

from pydantic import BaseModel, Field


class VariableState(BaseModel):
    variables: dict[str, Any] = Field(default_factory=dict)