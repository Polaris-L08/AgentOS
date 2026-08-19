from pydantic import BaseModel, Field

from reflection.reflection_state import ReflectionState
from runtime.context.history_state import HistoryState
from runtime.context.memory_state import MemoryState
from runtime.context.scratchpad_state import ScratchpadState
from runtime.context.variable_state import VariableState
from runtime.context.workspace_state import WorkspaceState


class AgentContext(BaseModel):
    """
    Agent的长期上下文
    """

    memory_state: MemoryState = Field(default_factory=MemoryState)

    scratchpad_state: ScratchpadState = Field(default_factory=ScratchpadState)

    history_state: HistoryState = Field(default_factory=HistoryState)

    workspace_state: WorkspaceState = Field(default_factory=WorkspaceState)

    reflection_state: ReflectionState = Field(default_factory=ReflectionState)

    variable_state: VariableState = Field(default_factory=VariableState)