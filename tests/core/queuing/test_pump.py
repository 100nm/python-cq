import math
from contextlib import nullcontext
from typing import Any

import anyio
import anyio.lowlevel
import pytest

from cq import MemoryQueue, MiddlewareResult, Pump
from cq.middlewares.contextlib import ContextManagerMiddleware


class TestPump:
    def test_add_middlewares_with_success_returns_self(self) -> None:
        middleware = ContextManagerMiddleware(nullcontext())

        async def dispatcher(message: str) -> None: ...

        pump = Pump(MemoryQueue[str](), dispatcher)

        assert pump.add_middlewares(middleware) is pump

    async def test_drain_with_closed_queue_dispatches_sent_messages(self) -> None:
        dispatched = []

        async def dispatcher(message: str) -> None:
            dispatched.append(message)

        queue = MemoryQueue[str](math.inf)
        await queue.send("first")
        await queue.send("second")
        await queue.close()

        await Pump(queue, dispatcher).drain()

        assert dispatched == ["first", "second"]

    async def test_drain_with_middlewares_wraps_dispatcher(self) -> None:
        calls = []

        async def middleware(message: str) -> MiddlewareResult[Any]:
            calls.append(f"before {message}")
            yield
            calls.append(f"after {message}")

        async def dispatcher(message: str) -> None:
            calls.append(f"dispatch {message}")

        queue = MemoryQueue[str](math.inf)
        await queue.send("message")
        await queue.close()

        await Pump(queue, dispatcher).add_middlewares(middleware).drain()

        assert calls == ["before message", "dispatch message", "after message"]

    async def test_drain_with_dispatcher_error_raises_error(self) -> None:
        async def dispatcher(message: str) -> None:
            raise ValueError(message)

        queue = MemoryQueue[str](math.inf)
        await queue.send("message")
        await queue.close()

        with pytest.raises(ValueError, match="message"):
            await Pump(queue, dispatcher).drain()

    async def test_drain_with_dispatcher_error_and_fail_silently_dispatches_next_messages(
        self,
    ) -> None:
        dispatched = []

        async def dispatcher(message: str) -> None:
            dispatched.append(message)
            raise ValueError(message)

        queue = MemoryQueue[str](math.inf)
        await queue.send("first")
        await queue.send("second")
        await queue.close()

        await Pump(queue, dispatcher, fail_silently=True).drain()

        assert dispatched == ["first", "second"]

    @pytest.mark.parametrize("concurrency", [0, -1])
    async def test_draining_with_concurrency_less_than_1_raises_value_error(
        self,
        concurrency: int,
    ) -> None:
        async def dispatcher(message: str) -> None: ...

        pump = Pump(MemoryQueue[str](), dispatcher)

        with pytest.raises(ValueError, match="`concurrency` must be at least 1"):
            async with pump.draining(concurrency=concurrency):
                pass

    async def test_draining_with_concurrency_dispatches_messages_concurrently(
        self,
    ) -> None:
        started = []
        all_started = anyio.Event()

        async def dispatcher(message: str) -> None:
            started.append(message)
            if len(started) == 2:
                all_started.set()

            await all_started.wait()

        queue = MemoryQueue[str](math.inf)

        with anyio.fail_after(1):
            async with Pump(queue, dispatcher).draining(concurrency=2, graceful=True):
                await queue.send("first")
                await queue.send("second")
                await queue.close()

        assert started == ["first", "second"]

    async def test_draining_with_graceful_waits_for_remaining_messages(self) -> None:
        dispatched = []

        async def dispatcher(message: str) -> None:
            await anyio.lowlevel.checkpoint()
            dispatched.append(message)

        queue = MemoryQueue[str](math.inf)

        async with Pump(queue, dispatcher).draining(graceful=True):
            await queue.send("first")
            await queue.send("second")
            await queue.close()

        assert dispatched == ["first", "second"]

    async def test_draining_without_graceful_cancels_dispatch_in_progress(
        self,
    ) -> None:
        started = anyio.Event()
        cancelled = []

        async def dispatcher(message: str) -> None:
            started.set()

            try:
                await anyio.sleep_forever()
            except anyio.get_cancelled_exc_class():
                cancelled.append(message)
                raise

        queue = MemoryQueue[str](math.inf)

        async with Pump(queue, dispatcher).draining():
            await queue.send("message")
            await started.wait()

        assert cancelled == ["message"]
