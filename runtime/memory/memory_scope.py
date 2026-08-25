from dataclasses import dataclass
from enum import Enum

class MemoryScopeType(str, Enum):
    """
    Defines the ownership boundary of a Memory scope.
    """

    AGENT = "agent"
    AGENT_TYPE = "agent_type"


@dataclass(frozen=True, slots=True)
class MemoryScope:
    """
    Identifies the logical ownership boundary of Memory.

    A MemoryScope does not contain Memory data.
    It only identifies where the Memory belongs.
    """

    type: MemoryScopeType
    id: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError(
                "MemoryScope id must not be empty."
            )