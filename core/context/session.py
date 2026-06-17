from pydantic import BaseModel, Field

from core.context.metadata import ContextMetadata
from core.context.state import ContextState
from core.tools.patch import ContextPatch


class SessionContext(BaseModel):

    state: ContextState = Field(default_factory=ContextState)

    metadata: ContextMetadata = Field(default_factory=ContextMetadata)

    def apply_patch(
            self,
            patch: ContextPatch
    ) -> "SessionContext":

        new_state = self.state.apply_patch(patch)

        return SessionContext(
            state=new_state,
            metadata=self.metadata
        )