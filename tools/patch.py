from typing import Any, Literal
from pydantic import BaseModel, Field


class ContextPatch(BaseModel):
    """
    Describe how a tool intends to mutate Context
    """

    # updates: dict[str, Any] = Field(default_factory=dict)

    target: Literal[
        "history",
        "memory",
        "workspace",
        "variable",
        "scratchpad"
    ]

    op: Literal[
        "append",
        "set",
        "delete",
        "update"
    ]

    value: Any