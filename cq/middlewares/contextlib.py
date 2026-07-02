from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncContextManager, ContextManager

if TYPE_CHECKING:  # pragma: no cover
    from cq import MiddlewareResult

__all__ = ("AsyncContextManagerMiddleware", "ContextManagerMiddleware")


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class AsyncContextManagerMiddleware:
    context: AsyncContextManager[Any]

    async def __call__(self, /, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        async with self.context:
            yield


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ContextManagerMiddleware:
    context: ContextManager[Any]

    async def __call__(self, /, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        with self.context:
            yield
