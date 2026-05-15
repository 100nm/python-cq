from typing import Any

import anyio
import pytest

from cq import MemoryQueue, MiddlewareResult, Pump


class TestPump:
    async def test_draining_without_graceful(self) -> None:
        dispatched = anyio.Event()

        async def dispatcher(message: str) -> None:
            await anyio.sleep(60)
            dispatched.set()  # pragma: no cover

        queue = MemoryQueue[str]()

        async with Pump(queue, dispatcher).draining(graceful=False):
            await queue.send("message")

        assert not dispatched.is_set()

    async def test_draining_with_middleware(self) -> None:
        entered = anyio.Event()
        exited = anyio.Event()

        async def middleware(message: str) -> MiddlewareResult[Any]:
            entered.set()
            try:
                yield
            finally:
                exited.set()

        async def dispatcher(message: str) -> None: ...

        queue = MemoryQueue[str]()

        async with Pump(queue, dispatcher).add_middlewares(middleware).draining():
            await queue.send("message")

        assert entered.is_set() and exited.is_set()

    async def test_draining_when_concurrency_is_less_than_1_raise_value_error(
        self,
    ) -> None:
        async def dispatcher(message: str) -> None: ...

        queue = MemoryQueue[str]()

        with pytest.raises(ValueError):
            async with Pump(queue, dispatcher).draining(concurrency=0):
                raise NotImplementedError
