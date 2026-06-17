from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from core.context.session import SessionContext
from core.tools.result import ToolResult


@dataclass
class ToolPolicy:
    """
    A tool policy is a set of rules that define how a tool can be used.
    """

    timeout: int = 30

    retry: int = 0

    execution_mode: str = "local"


class AbstractTool(ABC):
    """
    Abstract class for all tools.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    def policy(self) -> ToolPolicy:
        return ToolPolicy()

    @abstractmethod
    async def execute(
            self,
            input: Any,
            context: SessionContext
    ) -> ToolResult:
        ...