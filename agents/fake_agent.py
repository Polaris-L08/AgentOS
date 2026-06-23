from agents.base_agent import AbstractAgent
from core.context.session import SessionContext
from core.tools.executor import ToolExecutor


class FakeAgent(AbstractAgent):

    executor: ToolExecutor

    async def run(
            self,
            tool_name: str,
            arguments: dict,
            session: SessionContext
    ) -> SessionContext:
        ...