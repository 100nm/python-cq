from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from typing import Any, Self

import anyio
from anyio.abc import ObjectReceiveStream, ObjectSendStream

from cq._core.middleware import Middleware
from cq._core.pump import Pump
from cq._core.queues.abc import Queue


class MemoryQueue[T](Queue[T]):
    __slots__ = ("__consumer", "__producer")

    __consumer: ObjectReceiveStream[T]
    __producer: ObjectSendStream[T]

    def __init__(self, maxsize: int = 0) -> None:
        self.__producer, self.__consumer = anyio.create_memory_object_stream(maxsize)

    def __aiter__(self) -> AsyncIterator[T]:
        return aiter(self.__consumer)

    async def close(self) -> None:
        await self.__producer.aclose()

    @asynccontextmanager
    async def draining(
        self,
        dispatcher: Callable[[T], Awaitable[Any]],
        /,
        *,
        concurrency: int | None = None,
        fail_silently: bool = False,
        middlewares: Sequence[Middleware[[T], Any]] = (),
    ) -> AsyncIterator[Self]:
        async with (
            Pump(self, dispatcher, fail_silently)
            .add_middlewares(*middlewares)
            .draining(concurrency=concurrency, graceful=True)
        ):
            try:
                yield self
            finally:
                await self.close()

    async def send(self, message: T, /) -> None:
        await self.__producer.send(message)
