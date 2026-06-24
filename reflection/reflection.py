from pydantic import BaseModel, Field


class Reflection(BaseModel):
    summary: str

    suggestions: list[str] = Field(default_factory=list)