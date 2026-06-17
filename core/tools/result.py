from typing import Any
from pydantic import BaseModel, Field
from core.tools.patch import ContextPatch


class ToolResult(BaseModel):
    success: bool

    output: Any = None

    error: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    patch: ContextPatch | None = None
