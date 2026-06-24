from pydantic import BaseModel, Field

from context.history_state import HistoryState
from context.memory_state import MemoryState
from context.scratchpad_state import ScratchpadState
from context.variable_state import VariableState
from context.workspace_state import WorkspaceState
from reflection.reflection_state import ReflectionState


class ContextState(BaseModel):

    history: HistoryState = Field(default_factory=HistoryState)

    scratchpad: ScratchpadState = Field(default_factory=ScratchpadState)

    memory: MemoryState = Field(default_factory=MemoryState)

    workspace: WorkspaceState = Field(default_factory=WorkspaceState)

    variables: VariableState = Field(default_factory=VariableState)

    reflections: ReflectionState = Field(default_factory=ReflectionState)
