from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolRequest:
    tool_name: str

    arguments: dict[str, Any] = field(default_factory=dict)