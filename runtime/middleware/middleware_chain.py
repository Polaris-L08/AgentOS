from typing import Iterable, Any

from runtime.context.context_state import ContextState
from runtime.middleware.base_middleware import Middleware
from runtime.middleware.runtime_operation import RuntimeOperation
from runtime.runtime_context import RuntimeContext


class MiddlewareChain:

    def __init__(
        self,
        middlewares: Iterable[Middleware] | None = None,
    ):
        self._middlewares = list(middlewares or [])

    async def before(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
    ) -> None:
        for middleware in self._middlewares:
            await middleware.before(operation, runtime_context)

    async def after(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
        result: Any,
    ) -> None:
        for middleware in reversed(self._middlewares):
            await middleware.after(
                operation,
                runtime_context,
                result,
            )

    async def on_error(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
        error: Exception,
    ) -> None:
        for middleware in reversed(self._middlewares):
            await middleware.on_error(
                operation,
                runtime_context,
                error,
            )