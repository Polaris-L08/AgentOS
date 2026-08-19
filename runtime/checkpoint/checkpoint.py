import uuid

from pydantic import BaseModel, Field

from runtime.context.context_state import ContextState
from runtime.context.shared_context import SharedContext
from runtime.loop.loop_state import LoopState


class AgentCheckpoint(BaseModel):
    """
    Checkpoint for one Agent execution.

    Lifecycle:
        AgentExecutionContext
                |
            checkpoint
    """
    agent_id: str

    status: str = "RUNNING"

    state: ContextState

    loop: LoopState

class Checkpoint(BaseModel):
    """
    Runtime Snapshot.

    Stores:
        Runtime shared state
        Agent execution states
    """
    checkpoint_id: str = Field(default_factory=lambda : str(uuid.uuid4()))

    runtime_id: str

    shared_context: SharedContext

    agents: dict[str, AgentCheckpoint] = Field(default_factory=dict)

    # backward compatibility

    task_id: str | None

    # create_at: datetime = Field(default_factory=datetime.utcnow)