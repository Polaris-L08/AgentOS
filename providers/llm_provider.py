from abc import ABC, abstractmethod

from providers.llm_response import LLMResponse
from providers.prompt_message import PromptMessage


class LLMProvider(ABC):

    @abstractmethod
    async def generate(self, messages: list[PromptMessage]) -> LLMResponse:
        pass