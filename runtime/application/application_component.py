from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ApplicationComponent(Protocol):
    """
    Lifecycle contract for components managed by AgentApplication.

    Application-level lifecycle orchestration is optional. A component
    participates in Application lifecycle management only when it implements
    this contract.

    The Application owns the orchestration order; the component owns its
    internal resource lifecycle.
    """

    async def initialize(self) -> None:
        """Prepare the component for runtime use."""
        ...

    async def start(self) -> None:
        """Start the component's active runtime behavior."""
        ...

    async def stop(self) -> None:
        """Release component resources and stop active behavior."""
        ...