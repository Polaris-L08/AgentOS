from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResearchTask:
    """
    Domain task for an investment research Agent.

    This model describes WHAT the Agent needs to research.

    It does not describe HOW the task is executed.

    Runtime concerns such as:
        - execution lifecycle
        - middleware
        - tracing
        - checkpoint
        - retry

    do not belong here.
    """
    task_id: str

    subject: str

    objective: str

    @property
    def description(self) -> str:
        """
        Human-readable description of the research task.
        """
        return (
            f"Research subject: {self.subject}."
            f"Objective: {self.objective}."
        )