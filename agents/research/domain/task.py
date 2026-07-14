from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class ResearchTaskStatus(str, Enum):
    PENDING = "pending"

    RUNNING = "running"

    COMPLETED = "completed"

    FAILED = "failed"


@dataclass
class ResearchTask:
    task_id: str = field(default_factory=lambda : str(uuid4()))

    description: str = ""

    status: ResearchTaskStatus = ResearchTaskStatus.PENDING

    result: str | None = None