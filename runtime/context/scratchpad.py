from pydantic import BaseModel, Field


class Scratchpad(BaseModel):
    current_goal: str = ""

    hypothesis: str = ""

    next_action: str = ""

    notes: list[str] = Field(default_factory=list)