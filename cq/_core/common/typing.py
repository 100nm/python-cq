from typing import Protocol


class Decorator(Protocol):
    def __call__[T](self, wrapped: T, /) -> T: ...
