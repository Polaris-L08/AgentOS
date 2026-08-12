from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResearchGoal:
    """
    Defines the expected outcome of an investment research task.

    A goal describes what the Agent should eventually produce,
    rather than how the Agent should achieve it.
    """

    objective: str

    required_topics: tuple[str, ...] = field(default_factory=tuple)

    success_criteria: tuple[str, ...] = field(default_factory=tuple)