from core.context.session import SessionContext


class AbstractAgent:
    async def run(
            self,
            tool_name: str,
            arguments: dict,
            session: SessionContext
    ) -> SessionContext:
        ...