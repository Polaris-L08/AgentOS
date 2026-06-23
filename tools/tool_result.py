from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    success: bool

    output: str

    metadata: dict[str, Any] = None