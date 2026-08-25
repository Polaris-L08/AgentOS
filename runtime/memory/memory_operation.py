from enum import Enum

class MemoryOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"