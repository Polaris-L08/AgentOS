from pydantic import BaseModel, Field

from context.history_state import HistoryState
from context.scratchpad_state import ScratchpadState


class ContextState(BaseModel):

    history: HistoryState = Field(default_factory=HistoryState)

    scratchpad: ScratchpadState = Field(default_factory=ScratchpadState)