from pydantic import BaseModel, Field

from runtime.context.agent_state import AgentState


class ContextState(BaseModel):

    agent_context: AgentState = Field(default_factory=AgentState)

    # 业务领域
    domain_context: BaseModel | None