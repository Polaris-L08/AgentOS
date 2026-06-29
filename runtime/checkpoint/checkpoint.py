from datetime import datetime

from pydantic import BaseModel, Field

from runtime.loop.loop_state import LoopState
from runtime.context.context_state import ContextState
from models.task_request import TaskRequest


class Checkpoint(BaseModel):
    """
    Runtime Snapshot
    """

    version: int = 1

    task_request: TaskRequest

    loop_state: LoopState

    context_state: ContextState

    create_at: datetime = Field(default_factory=datetime.utcnow)