from pydantic import BaseModel, Field

from runtime.context.memory_item import MemoryItem


class MemoryState(BaseModel):

    items: list[MemoryItem] = Field(default_factory=list)