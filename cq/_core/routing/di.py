from __future__ import annotations

from abc import abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any, Concatenate, Protocol, runtime_checkable

from cq.middlewares.contextlib import AsyncContextManagerMiddleware

if TYPE_CHECKING:  # pragma: no cover
    from cq import Command, CommandBus, EventBus, Middleware, QueryBus


@runtime_checkable
class DIAdapter(Protocol):
    """
    Protocol for integrating a dependency injection container with python-cq.

    Implement this protocol to connect your DI framework to the CQ buses.
    A concrete implementation (``InjectionAdapter``) is provided via the
    ``python-cq[injection]`` extra for projects that use *python-injection*.
    """

    __slots__ = ()

    @abstractmethod
    def command_scope(self) -> Middleware[Concatenate[Command, ...], Any]:
        """
        Return a middleware that wraps each command dispatch.

        **Responsibilities**

        The middleware must at minimum manage the lifecycle of a
        ``RelatedEvents`` instance and register it so that it is resolvable
        via injection for the duration of the dispatch.

        If you already have an async context manager for the scope, wrap it
        with ``cq.middlewares.contextlib.AsyncContextManagerMiddleware``
        instead of writing the middleware by hand.
        """

        raise NotImplementedError

    @abstractmethod
    def lazy[T](self, tp: type[T]) -> Callable[[], Awaitable[T]]:
        """
        Return a callable that resolves an instance of ``tp`` in two steps.

        1. ``lazy(tp)`` obtains a resolver from the DI framework for ``tp``.
        2. Calling and awaiting the returned callable performs the actual
           resolution and returns the instance.
        """

        raise NotImplementedError

    def register_defaults(
        self,
        command_bus: Callable[..., CommandBus[Any]],
        event_bus: Callable[..., EventBus],
        query_bus: Callable[..., QueryBus[Any]],
    ) -> None:
        """
        Register the CQ buses as default providers in the DI container.

        Called once during setup so that handlers and middlewares can
        declare ``CommandBus``, ``EventBus``, or ``QueryBus`` as
        constructor dependencies and receive the configured instances.

        The default implementation is a no-op for adapters that do not
        need automatic bus registration.
        """

        return

    @abstractmethod
    def wire[T](self, tp: type[T]) -> Callable[..., Awaitable[T]]:
        """
        Return an async factory that instantiates ``tp`` with injected
        dependencies.

        Used internally to build handler instances whose dependencies are
        resolved by the container.
        """

        raise NotImplementedError


class NoDI(DIAdapter):
    __slots__ = ()

    def command_scope(self) -> Middleware[Concatenate[Command, ...], Any]:
        return AsyncContextManagerMiddleware(nullcontext())

    def lazy[T](self, tp: type[T], /) -> Callable[[], Awaitable[T]]:
        tp_str = getattr(tp, "__name__", str(tp))
        raise RuntimeError(
            f"Can't lazily resolve {tp_str}: no DI container configured."
        )

    def wire[T](self, tp: type[T], /) -> Callable[..., Awaitable[T]]:
        async def factory() -> T:
            return tp()

        return factory
