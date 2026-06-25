from pydantic import BaseModel, Field

from context.history_state import HistoryState
from context.memory_state import MemoryState
from context.scratchpad_state import ScratchpadState
from context.variable_state import VariableState
from context.workspace_state import WorkspaceState
from core.tools.patch import ContextPatch
from reflection.reflection_state import ReflectionState


class ContextState(BaseModel):

    history_state: HistoryState = Field(default_factory=HistoryState)

    scratchpad_state: ScratchpadState = Field(default_factory=ScratchpadState)

    memory_state: MemoryState = Field(default_factory=MemoryState)

    workspace_state: WorkspaceState = Field(default_factory=WorkspaceState)

    variables_state: VariableState = Field(default_factory=VariableState)

    reflections_state: ReflectionState = Field(default_factory=ReflectionState)

    def apply_patch(self, patch: ContextPatch) -> "ContextState":

        if patch.target == "workspace":
            self.workspace_state = self.workspace_state.apply(patch)

        elif patch.target == "memory":
            self.memory_state = self.memory_state.apply(patch)

        elif patch.target == "history":
            self.history_state = self.history_state.apply(patch)

        elif patch.target == "variable":
            self.variables_state = self.variables_state.apply(patch)

        elif patch.target == "scratchpad":
            self.scratchpad_state = self.scratchpad_state.apply(patch)

        return self
