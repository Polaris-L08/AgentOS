from actions.observation import Observation
from providers.llm_provider import LLMProvider
from providers.prompt_message import PromptMessage
from reflection.reflection import Reflection


class CriticAgent:

    def __init__(self, llm_provider: LLMProvider):
        self._llm_provider = llm_provider

    async def reflect(self, observations: list[Observation]) -> Reflection:
        history = "\n".join(
            str(obs)
            for obs in observations
        )

        messages = [
            PromptMessage(
                role="system",
                content=f"""
                You are a critic agent.

                Analyze the execution history.
                
                Return JSON:
                
                {
                "summary": "...",
                  "suggestions": ["...", "..."]
                }
"""
            ),
            PromptMessage(
                role="user",
                content=history
            )
        ]

        response = await self._llm_provider.generate(messages)

        return Reflection.model_validate_json(response.content)
