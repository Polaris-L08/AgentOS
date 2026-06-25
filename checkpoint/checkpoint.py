from datetime import datetime

from pydantic import BaseModel, Field

from agents.loop_state import LoopState
from context.context_state import ContextState
from core.task_request import TaskRequest


class Checkpoint(BaseModel):
    """
    Runtime Snapshot
    """

    version: int = 1

    task_request: TaskRequest

    loop_state: LoopState

    context_state: ContextState

    create_at: datetime = Field(default_factory=datetime.utcnow)