from contextlib import nullcontext
from typing import Any, Self

import pytest

from cq import ContextPipeline, MiddlewareResult, Pipe
from cq._core.routing.dispatchers.bus import SimpleBus
from cq.middlewares.contextlib import ContextManagerMiddleware


class _LengthHandler:
    async def handle(self, message: str) -> int:
        return len(message)

    @classmethod
    async def factory(cls) -> Self:
        return cls()


class _StarsHandler:
    async def handle(self, message: int) -> str:
        return "*" * message

    @classmethod
    async def factory(cls) -> Self:
        return cls()


class _ReverseHandler:
    async def handle(self, message: str) -> str:
        return message[::-1]

    @classmethod
    async def factory(cls) -> Self:
        return cls()


def _double(length: int) -> int:
    return length * 2


@pytest.fixture
def bus() -> SimpleBus[Any, Any]:
    return (
        SimpleBus[Any, Any]()
        .subscribe(str, _LengthHandler.factory)
        .subscribe(int, _StarsHandler.factory)
    )


class TestPipe:
    async def test_dispatch_without_steps_returns_dispatcher_result(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        pipe = Pipe[str, int](bus)

        assert await pipe.dispatch("hello") == 5

    async def test_dispatch_with_sync_step_returns_last_dispatch_result(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        pipe = Pipe[str, str](bus)
        pipe.step(_double)

        assert await pipe.dispatch("hello") == "**********"

    async def test_dispatch_with_async_step_returns_last_dispatch_result(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        pipe = Pipe[str, str](bus)

        @pipe.step
        async def _(length: int) -> int:
            return length * 2

        assert await pipe.dispatch("hello") == "**********"

    async def test_dispatch_with_step_dispatcher_dispatches_next_message_with_it(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        other_bus = SimpleBus[str, str]().subscribe(str, _ReverseHandler.factory)
        pipe = Pipe[str, str](bus)

        @pipe.step
        def _(length: int) -> int:
            return length

        @pipe.step(dispatcher=other_bus)
        def _(stars: str) -> str:
            return f"{stars}!"

        assert await pipe.dispatch("hello") == "!*****"

    async def test_dispatch_with_step_returning_none_returns_not_implemented(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        pipe = Pipe[str, str](bus)

        @pipe.step
        def _(length: int) -> None:
            return None

        assert await pipe.dispatch("hello") is NotImplemented

    async def test_dispatch_with_static_step_dispatches_static_message(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        pipe = Pipe[str, str](bus).add_static_step(2)

        assert await pipe.dispatch("hello") == "**"

    def test_step_with_success_returns_wrapped_function(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        pipe = Pipe[str, str](bus)

        assert pipe.step(_double) is _double
        assert pipe.step(dispatcher=bus)(_double) is _double


class TestContextPipeline:
    def test_get_without_instance_and_owner_returns_self(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        pipeline = ContextPipeline[str](bus)

        assert pipeline.__get__() is pipeline

    def test_add_middlewares_with_success_returns_self(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        middleware = ContextManagerMiddleware(nullcontext())
        pipeline = ContextPipeline[str](bus)

        assert pipeline.add_middlewares(middleware) is pipeline

    async def test_dispatch_with_class_access_returns_new_context(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        class Context:
            length: int

            pipeline = ContextPipeline[str](bus)

            @pipeline.step
            def _(self, length: int) -> int:
                self.length = length
                return length

        context = await Context.pipeline.dispatch("hello")

        assert isinstance(context, Context)
        assert context.length == 5

    async def test_dispatch_with_instance_access_returns_same_instance(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        class Context:
            pipeline = ContextPipeline[str](bus)

        context = Context()

        assert await context.pipeline.dispatch("hello") is context

    async def test_dispatch_with_async_step_returns_context(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        class Context:
            length: int

            pipeline = ContextPipeline[str](bus)

            @pipeline.step
            async def _(self, length: int) -> int:
                self.length = length
                return length

        context = await Context.pipeline.dispatch("hello")

        assert context.length == 5

    async def test_dispatch_with_static_step_dispatches_static_message(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        dispatched = []

        class Handler:
            async def handle(self, message: int) -> None:
                dispatched.append(message)

            @classmethod
            async def factory(cls) -> Self:
                return cls()

        other_bus = SimpleBus[int, None]().subscribe(int, Handler.factory)

        class Context:
            pipeline = ContextPipeline[str](bus).add_static_step(2, other_bus)

        await Context.pipeline.dispatch("hello")

        assert dispatched == [2]

    async def test_dispatch_with_middlewares_wraps_pipeline(
        self,
        bus: SimpleBus[Any, Any],
    ) -> None:
        calls = []

        async def middleware(message: str) -> MiddlewareResult[Any]:
            calls.append(f"before {message}")
            yield
            calls.append(f"after {message}")

        class Context:
            pipeline = ContextPipeline[str](bus).add_middlewares(middleware)

            @pipeline.step
            def _(self, length: int) -> int:
                calls.append(f"step {length}")
                return length

        await Context.pipeline.dispatch("hello")

        assert calls == ["before hello", "step 5", "after hello"]
