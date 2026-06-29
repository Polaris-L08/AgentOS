import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MemorySource(str, Enum):
    HISTORY = "history"

    TOOL = "tool"

    REFLECTION = "reflection"

class MemoryItem(BaseModel):

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    content: str

    importance: float = 1.0

    source: MemorySource = MemorySource.HISTORY

    timestamp: str = Field(default_factory=lambda: str(datetime.utcnow))