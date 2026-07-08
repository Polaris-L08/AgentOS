import pytest

from runtime.component.runtime_component import RuntimeComponent
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.runtime_operation import RuntimeOperation


class MockRuntimeComponent(RuntimeComponent):
    pass


class RecordingMiddleware:

    def __init__(self):
        self.events = []


    async def before(
        self,
        operation,
        runtime_context,
    ):
        self.events.append(
            "before"
        )


    async def after(
        self,
        operation,
        runtime_context,
        result,
    ):
        self.events.append(
            "after"
        )


    async def on_error(
        self,
        operation,
        runtime_context,
        error,
    ):
        self.events.append(
            "error"
        )


@pytest.mark.asyncio
async def test_runtime_component_success():

    middleware = RecordingMiddleware()

    component = MockRuntimeComponent(
        MiddlewareChain(
            [
                middleware
            ]
        )
    )


    async def operation():
        return "ok"


    result = await component.invoke(
        RuntimeOperation(
            name="test",
            component="test",
            metadata={}
        ),
        runtime_context=None,
        func=operation,
    )


    assert result == "ok"

    assert middleware.events == [
        "before",
        "after",
    ]



@pytest.mark.asyncio
async def test_runtime_component_error():

    middleware = RecordingMiddleware()

    component = MockRuntimeComponent(
        MiddlewareChain(
            [
                middleware
            ]
        )
    )


    async def operation():
        raise RuntimeError(
            "failed"
        )


    with pytest.raises(
        RuntimeError
    ):

        await component.invoke(
            RuntimeOperation(
                name="test",
                component="test",
                metadata={}
            ),
            runtime_context=None,
            func=operation,
        )


    assert middleware.events == [
        "before",
        "error",
    ]