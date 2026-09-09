from dataclasses import dataclass


@dataclass(frozen=True)
class TaskRequest:
    task_id: str
    user_input: str
    session_id: str | None = None