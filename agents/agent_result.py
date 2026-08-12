from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentResult:
    """
    Result returned from one Agent execution.

    This object represents communication between Agents.

    It is NOT:
        - final user task result
        - tool result
        - runtime exception

    Example:

        SupervisorAgent
              |
              |
        ResearchAgent
              |
              |
        AgentResult
    """

    success: bool

    output: Any | None = None

    observations: list[Any] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)