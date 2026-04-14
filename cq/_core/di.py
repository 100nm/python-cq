from __future__ import annotations

from abc import abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any, AsyncContextManager, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cq._core.message import CommandBus, EventBus, QueryBus


@runtime_checkable
class DIAdapter(Protocol):
    __slots__ = ()

    @abstractmethod
    def command_scope(self) -> AsyncContextManager[None]:
        raise NotImplementedError

    @abstractmethod
    def lazy[T](self, tp: type[T]) -> Callable[[], Awaitable[T]]:
        raise NotImplementedError

    def register_defaults(
        self,
        command_bus: Callable[..., CommandBus[Any]],
        event_bus: Callable[..., EventBus],
        query_bus: Callable[..., QueryBus[Any]],
    ) -> None:
        return

    @abstractmethod
    def wire[T](self, tp: type[T]) -> Callable[..., Awaitable[T]]:
        raise NotImplementedError


class NoDI(DIAdapter):
    __slots__ = ()

    def command_scope(self) -> AsyncContextManager[None]:
        return nullcontext()

    def lazy[T](self, tp: type[T], /) -> Callable[[], Awaitable[T]]:
        tp_str = getattr(tp, "__name__", str(tp))
        raise RuntimeError(
            f"Can't lazily resolve {tp_str}: no DI container configured."
        )

    def wire[T](self, tp: type[T], /) -> Callable[..., Awaitable[T]]:
        async def factory() -> T:
            return tp()

        return factory
