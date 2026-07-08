from abc import ABC
from typing import TypeVar, Callable, Awaitable, Any

from runtime.context.runtime_context import RuntimeContext
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.runtime_operation import RuntimeOperation

T = TypeVar("T")

class RuntimeComponent(ABC):
    """
    Base class for runtime components.

    RuntimeComponent provides a unified execution boundary
    with middleware lifecycle support.

    Responsibilities:

    - execute middleware before hook
    - execute component operation
    - execute middleware after hook
    - execute middleware error hook

    It does NOT define business behavior.

    Examples:

        AgentRuntime
        ToolExecutor
        MemoryRuntime
        WorkflowRuntime

    can inherit this abstraction.
    """

    def __init__(self, middleware_chain: MiddlewareChain | None = None):
        self._middleware_chain = middleware_chain

    async def invoke(
            self,
            operation: RuntimeOperation,
            runtime_context: RuntimeContext,
            func: Callable[..., Awaitable[T]],
            *args: Any,
            **kwargs: Any
    ) -> T:
        """
        Execute a runtime operation with middleware lifecycle.

        Flow:

            before()

              ↓

            func()

              ↓

            after()


        Error:

            func()

              ↓

            on_error()

              ↓

            raise


        RuntimeComponent does not transform
        business exceptions.

        Business components decide whether an
        exception represents a domain failure.
        """
        if self._middleware_chain is None:
            return await func(*args, **kwargs)

        await self._middleware_chain.before(operation, runtime_context)

        try:
            result = await func(*args, **kwargs)

        except Exception as e:
            await self._middleware_chain.on_error(operation, runtime_context, e)
            raise

        else:
            await self._middleware_chain.after(operation, runtime_context, result)
            return result

