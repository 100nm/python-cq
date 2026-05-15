from abc import abstractmethod
from collections.abc import AsyncIterator
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
class Consumer[T](Protocol):
    __slots__ = ()

    @abstractmethod
    def __aiter__(self) -> AsyncIterator[T]:
        raise NotImplementedError


@runtime_checkable
class Queue[T](Producer[T], Consumer[T], Protocol):
    __slots__ = ()
