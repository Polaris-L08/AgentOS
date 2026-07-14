from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class ResearchGoal:
    goal_id: str = field(default_factory=lambda : str(uuid4()))

    description: str = ""

    created_at: datetime = field(default_factory=datetime.utcnow)
