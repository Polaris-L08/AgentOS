from pydantic import BaseModel, Field

from context.memory_item import MemoryItem


class MemoryState(BaseModel):

    items: list[MemoryItem] = Field(default_factory=list)