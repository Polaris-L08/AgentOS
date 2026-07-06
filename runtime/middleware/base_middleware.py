from abc import ABC, abstractmethod
from typing import Any

from runtime.context.context_state import ContextState
from runtime.middleware.runtime_operation import RuntimeOperation
from runtime.runtime_context import RuntimeContext


class Middleware(ABC):

    @abstractmethod
    async def before(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
    ) -> None:
        ...

    @abstractmethod
    async def after(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
        result: Any,
    ) -> None:
        ...

    @abstractmethod
    async def on_error(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
        error: Exception,
    ) -> None:
        ...