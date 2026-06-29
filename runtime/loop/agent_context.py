from pydantic import BaseModel

from runtime.context.context_state import ContextState


class AgentContext(BaseModel):
    state: ContextState