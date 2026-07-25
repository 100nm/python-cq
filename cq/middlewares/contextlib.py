from __future__ import annotations

from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from cq import MiddlewareResult

__all__ = ("AsyncContextManagerMiddleware", "ContextManagerMiddleware")


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class AsyncContextManagerMiddleware:
    context: AbstractAsyncContextManager[Any]

    async def __call__(self, /, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        async with self.context:
            yield


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ContextManagerMiddleware:
    context: AbstractContextManager[Any]

    async def __call__(self, /, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        with self.context:
            yield
