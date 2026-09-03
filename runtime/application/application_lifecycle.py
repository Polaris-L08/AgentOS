from enum import Enum


class ApplicationState(str, Enum):
    CREATED = "created"
    INITIALIZED = "initialized"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


class ApplicationLifecycleError(RuntimeError):
    """
    Raised when an invalid Application lifecycle transition
    is requested.
    """