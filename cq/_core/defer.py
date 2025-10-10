from abc import abstractmethod
from typing import Protocol


class DeferredBus[I](Protocol):
    __slots__ = ()

    @abstractmethod
    async def defer(self, input_value: I, /) -> None:
        raise NotImplementedError
