from dataclasses import dataclass

from runtime.memory.memory_operation import MemoryOperation


@dataclass(frozen=True, slots=True)
class MemoryAccessPolicy:
    """
    Defines which operations a MemoryRuntime may perform.

    The policy is intentionally small. It is an execution-time
    capability boundary, not a full RBAC/ABAC authorization system.
    """

    allow_read: bool = True
    allow_write: bool = True
    allow_delete: bool = False

    def allows(self, operation: MemoryOperation) -> bool:
        if operation is MemoryOperation.READ:
            return self.allow_read

        if operation is MemoryOperation.WRITE:
            return self.allow_write

        if operation is MemoryOperation.DELETE:
            return self.allow_delete

        return False
