from pydantic import BaseModel, Field

from context.scratchpad import Scratchpad


class ScratchpadState(BaseModel):

    scratchpad: Scratchpad = Field(default_factory=Scratchpad)