from typing import Protocol

from runtime.memory.memory_scope import MemoryScope


class MemoryScopeResolver(Protocol):
    """
    Resolves the Memory scopes available to a MemoryRuntime.

    The resolver only determines scope.
    It does not read or modify Memory.
    """

    def resolve(self) -> list[MemoryScope]:
        pass


class DefaultMemoryScopeResolver(MemoryScopeResolver):
    """
    Default explicit MemoryScopeResolver implementation.

    Scope ordering represents scope priority.

    For example:

        [
            AGENT("research-001"),
            AGENT_TYPE("research-agent"),
        ]

    means the Agent scope has higher priority than the
    Agent-Type scope.
    """
    def __init__(
            self,
            scopes: list[MemoryScope],
    ) -> None:
        self._scopes = list(scopes)

    def resolve(self) -> list[MemoryScope]:
        """
        Return the resolved scopes in priority order.

        A copy is returned so callers cannot mutate the
        resolver's internal state.
        """
        return list(self._scopes)