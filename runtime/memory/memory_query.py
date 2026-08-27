from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from runtime.context.memory_item import MemorySource
from runtime.memory.memory_scope import MemoryScope


class MemoryQuery(BaseModel):
    """
    Query constraints for retrieving Memory items
    within a single MemoryScope.

    MemoryQuery defines filtering constraints only.

    It does not define:
    - MemoryScope
    - ranking
    - semantic similarity
    - final result ordering
    """

    source: MemorySource | None = None

    min_importance: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    created_after: datetime | None = None

    created_before: datetime | None = None

    include_expired: bool = False

    limit: int | None = Field(
        default=None,
        gt=0,
    )