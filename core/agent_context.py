from pydantic import BaseModel


class AgentContext(BaseModel):
    state: ContextState