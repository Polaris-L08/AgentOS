from datetime import datetime, timezone

from pydantic import BaseModel, Field


class MemoryMetadata(BaseModel):
    """
    Lifecycle and retrieval metadata associated with a MemoryItem.
    """

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    expires_at: datetime | None = None