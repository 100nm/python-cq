from abc import abstractmethod
from collections.abc import AsyncIterable
from contextlib import AbstractAsyncContextManager
from typing import Protocol, runtime_checkable


@runtime_checkable
class Producer[T](Protocol):
    __slots__ = ()

    async def __call__(self, message: T, /) -> None:
        return await self.send(message)

    @abstractmethod
    async def send(self, message: T, /) -> None:
        raise NotImplementedError


@runtime_checkable
class Delivery[T](AbstractAsyncContextManager[T], Protocol):
    __slots__ = ()


@runtime_checkable
class Consumer[T](AsyncIterable[Delivery[T]], Protocol):
    __slots__ = ()


@runtime_checkable
class Queue[T](Producer[T], Consumer[T], Protocol):
    __slots__ = ()
