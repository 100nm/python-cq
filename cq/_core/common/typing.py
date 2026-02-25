from collections.abc import Callable
from typing import Any, Protocol, overload


class Decorator(Protocol):
    def __call__[T](self, wrapped: T, /) -> T: ...


class Method[**P, T](Protocol):
    @overload
    def __call__(self, instance: Any, /, *args: P.args, **kwargs: P.kwargs) -> T: ...

    @overload
    def __call__(self, /, *args: Any, **kwargs: Any) -> T: ...

    def __get__(
        self,
        instance: object,
        owner: type | None = ...,
        /,
    ) -> Callable[P, T]: ...
