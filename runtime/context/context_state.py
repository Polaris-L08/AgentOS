from pydantic import BaseModel, Field

from runtime.context.agent_context import AgentContext


class ContextState(BaseModel):

    agent_context: AgentContext = Field(default_factory=AgentContext)

    # 业务领域
    domain_context: BaseModel | None