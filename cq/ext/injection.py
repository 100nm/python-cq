from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, AsyncContextManager, Awaitable, Callable

from injection import Module, adefine_scope, mod
from injection.exceptions import ScopeAlreadyDefinedError

from cq._core.di import DIAdapter
from cq._core.message import CommandBus, EventBus, QueryBus
from cq._core.middleware import MiddlewareResult
from cq._core.related_events import AnyIORelatedEvents, RelatedEvents

__all__ = ("CQScope", "InjectionAdapter", "InjectionScopeMiddleware")


class CQScope(StrEnum):
    COMMAND_DISPATCH = "__cq_command_dispatch__"


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class InjectionAdapter(DIAdapter):
    module: Module = field(default_factory=mod)
    threadsafe: bool | None = field(default=None)

    def command_scope(self) -> AsyncContextManager[None]:
        return InjectionScopeMiddleware(  # type: ignore[return-value]
            CQScope.COMMAND_DISPATCH,
            exist_ok=True,
            threadsafe=self.threadsafe,
        )._cm

    def lazy[T](self, tp: type[T], /) -> Callable[[], Awaitable[T]]:
        awaitable = self.module.aget_lazy_instance(tp, threadsafe=self.threadsafe)
        return lambda: awaitable

    def register_defaults(
        self,
        command_bus: Callable[..., CommandBus[Any]],
        event_bus: Callable[..., EventBus],
        query_bus: Callable[..., QueryBus[Any]],
    ) -> None:
        self.module.injectable(
            command_bus,
            ignore_type_hint=True,
            inject=False,
            on=CommandBus,
            mode="fallback",
        )
        self.module.injectable(
            event_bus,
            ignore_type_hint=True,
            inject=False,
            on=EventBus,
            mode="fallback",
        )
        self.module.injectable(
            query_bus,
            ignore_type_hint=True,
            inject=False,
            on=QueryBus,
            mode="fallback",
        )
        self.module.scoped(
            CQScope.COMMAND_DISPATCH,
            mode="fallback",
        )(self.__new_related_events)

    def wire[T](self, tp: type[T], /) -> Callable[..., Awaitable[T]]:
        return self.module.make_async_factory(tp, self.threadsafe)

    @staticmethod
    async def __new_related_events(event_bus: EventBus) -> AsyncIterator[RelatedEvents]:
        async with AnyIORelatedEvents(event_bus) as events:
            yield events


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class InjectionScopeMiddleware:
    scope_name: str
    exist_ok: bool = field(default=False, kw_only=True)
    threadsafe: bool | None = field(default=None, kw_only=True)

    async def __call__(self, /, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        async with self._cm:  # type: ignore[attr-defined]
            yield

    @property
    @asynccontextmanager
    async def _cm(self) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            try:
                await stack.enter_async_context(
                    adefine_scope(self.scope_name, threadsafe=self.threadsafe)
                )

            except ScopeAlreadyDefinedError:
                if not self.exist_ok:
                    raise

            yield
