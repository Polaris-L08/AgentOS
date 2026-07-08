from __future__ import annotations

from typing import Any

from runtime.context.runtime_context import RuntimeContext
from runtime.middleware.base_middleware import Middleware
from runtime.middleware.runtime_operation import RuntimeOperation
from runtime.tracing.span import SpanStatus


class TracingMiddleware(Middleware):
    """
    Middleware responsible for tracing runtime execution.

    Lifecycle:

        before()
            -> start_span()

        after()
            -> end_span(SUCCESS)

        on_error()
            -> end_span(ERROR)
    """

    async def before(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
    ) -> None:
        runtime_context.trace.start_span(
            name=operation.name,
            metadata=operation.metadata
        )

    async def after(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
        result: Any,
    ) -> None:
        runtime_context.trace.end_span(
            status=SpanStatus.SUCCESS
        )

    async def on_error(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
        error: Exception,
    ) -> None:
        runtime_context.trace.end_span(
            status=SpanStatus.ERROR
        )