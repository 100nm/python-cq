from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Self

import anyio

from cq._core.middleware import Middleware, MiddlewareGroup, deliver_message
from cq._core.queues.abc import Consumer


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class Pump[T]:
    consumer: Consumer[T]
    dispatcher: Callable[[T], Awaitable[Any]]
    fail_silently: bool = field(default=False)
    __middleware_group: MiddlewareGroup[[T], Any] = field(
        default_factory=MiddlewareGroup,
        init=False,
    )

    def add_middlewares(self, *middlewares: Middleware[[T], Any]) -> Self:
        self.__middleware_group.add(*middlewares)
        return self

    async def drain(self) -> None:
        async for message in self.consumer:
            await deliver_message(
                message,
                self.dispatcher,
                self.__middleware_group,
                self.fail_silently,
            )

    @asynccontextmanager
    async def draining(
        self,
        /,
        *,
        concurrency: int | None = None,
        graceful: bool = False,
    ) -> AsyncIterator[None]:
        if concurrency is None:
            concurrency = 1
        elif concurrency < 1:
            raise ValueError(f"`concurrency` must be at least 1, got {concurrency}.")

        async with anyio.create_task_group() as task_group:
            for _ in range(concurrency):
                task_group.start_soon(self.drain)

            try:
                yield
            finally:
                if not graceful:
                    task_group.cancel_scope.cancel()
