from __future__ import annotations

from typing import Any, Protocol

class DurableState(Protocol):
    """
    Marker protocol for state that is safe to represent across
    a process boundary.

    DurableState is a data representation, not a live Runtime
    object and not a persistence mechanism.

    Concrete durable state models may define their own serialization
    mechanism according to their domain requirements.

    Examples:

        ExecutionState
        Checkpoint
        SessionState
        EventRecord
    """

    def model_dump(self) -> dict[str, Any]:
        """
        Return a serializable representation of the state.

        This method intentionally mirrors the interface commonly
        provided by Pydantic models without requiring DurableState
        implementations to inherit from a specific base class.
        """
        ...