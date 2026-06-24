from pydantic import BaseModel, Field

from reflection.reflection import Reflection


class ReflectionState(BaseModel):
    reflections: list[Reflection] = Field(default_factory=list)