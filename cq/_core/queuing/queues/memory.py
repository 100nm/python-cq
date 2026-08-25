from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager, nullcontext
from types import TracebackType
from typing import Any, Self

import anyio
from anyio.abc import ObjectReceiveStream, ObjectSendStream

from cq._core.middleware import Middleware
from cq._core.queuing.pump import Pump
from cq._core.queuing.queues.abc import Delivery, Queue


class MemoryQueue[T](Queue[T]):
    __slots__ = ("__consumer", "__producer")

    __consumer: ObjectReceiveStream[T]
    __producer: ObjectSendStream[T]

    def __init__(self, maxsize: float = 0) -> None:
        self.__producer, self.__consumer = anyio.create_memory_object_stream(maxsize)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def __aiter__(self) -> AsyncIterator[Delivery[T]]:
        async for message in self.__consumer:
            yield nullcontext(message)

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
            .draining(concurrency=concurrency, graceful=True),
            self,
        ):
            yield self

    async def send(self, message: T, /) -> None:
        await self.__producer.send(message)
