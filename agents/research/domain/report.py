from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ResearchReport:
    """
    Final domain result produced by a Research Agent.

    This is an Investment-domain object.

    It is not:
        - AgentResult
        - ToolResult
        - TaskResult
        - Runtime state
    """

    task_id: str

    subject: str

    summary: str

    findings: tuple[str, ...] = field(default_factory=tuple)

    risks: tuple[str, ...] = field(default_factory=tuple)

    evidence: tuple[dict[str, Any], ...] = field(
        default_factory=tuple
    )