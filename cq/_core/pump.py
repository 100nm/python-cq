from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import anyio

from cq._core.queues.abc import Consumer


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class Pump[T]:
    consumer: Consumer[T]
    dispatcher: Callable[[T], Awaitable[Any]]
    fail_silently: bool = field(default=False)

    async def drain(self) -> None:
        async for message in self.consumer:
            try:
                await self.dispatcher(message)
            except Exception:
                if not self.fail_silently:
                    raise

    @asynccontextmanager
    async def draining(self, /, *, graceful: bool = False) -> AsyncIterator[None]:
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(self.drain)

            try:
                yield
            finally:
                if not graceful:
                    task_group.cancel_scope.cancel()
