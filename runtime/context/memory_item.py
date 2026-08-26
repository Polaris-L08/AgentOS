import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from runtime.context.memory_metadata import MemoryMetadata


class MemorySource(str, Enum):
    HISTORY = "history"

    TOOL = "tool"

    REFLECTION = "reflection"

class MemoryItem(BaseModel):
    """
    A single piece of Agent Memory.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    content: str

    importance: float = 1.0

    source: MemorySource = MemorySource.HISTORY

    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)

    def is_expired(self) -> bool:
        """
        Return True when this MemoryItem has passed its
        expiration time.

        A MemoryItem without expires_at never expires.
        """

        if self.metadata.expires_at is None:
            return False

        return (
            self.metadata.expires_at
            <= datetime.now(timezone.utc)
        )