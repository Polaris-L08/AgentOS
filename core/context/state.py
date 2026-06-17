from pydantic import BaseModel, Field

from core.tools.patch import ContextPatch


class ContextState(BaseModel):

    working_dir: str = "."

    scratchpad: str = ""

    variables: dict[str, str] = Field(default_factory=dict)

    def apply_patch(
            self,
            patch: ContextPatch
    ) -> "ContextState":
        state_dict = self.model_dump()

        state_dict.update(patch.updates)

        return ContextState(**state_dict)