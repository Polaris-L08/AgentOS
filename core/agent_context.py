from pydantic import BaseModel

from context.context_state import ContextState


class AgentContext(BaseModel):
    state: ContextState