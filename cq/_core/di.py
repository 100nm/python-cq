from __future__ import annotations

from abc import abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any, AsyncContextManager, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from cq import CommandBus, EventBus, QueryBus


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
    def command_scope(self) -> AsyncContextManager[None]:
        """
        Return an async context manager that delimits the lifetime of a
        command dispatch.

        **Responsibilities**

        The scope must at minimum manage the lifecycle of a ``RelatedEvents``
        instance and register it so that it is resolvable via injection for
        the duration of the scope.

        **Nested calls**

        ``command_scope`` is entered in two distinct situations:

        1. Around a standard command dispatch (via
           ``CommandDispatchScopeMiddleware``).
        2. Around each step of a ``ContextCommandPipeline``, which itself
           wraps a command dispatch.

        This means two nested calls can occur for a single logical command.
        Implementations must detect re-entrant activation (e.g. a scope
        already active on the current task) and silently ignore the inner
        call instead of opening a second, conflicting scope.
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
