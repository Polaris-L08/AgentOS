from dataclasses import field
from datetime import datetime
from uuid import uuid4

from pydantic.dataclasses import dataclass


@dataclass
class ResearchReport:
    goal_id: str

    report_id: str = field(default_factory=lambda: str(uuid4()))

    summary: str = ""

    created_at: datetime = field(default_factory=datetime.utcnow())