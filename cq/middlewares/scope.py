from __future__ import annotations

from typing import TYPE_CHECKING, Any

from injection import adefine_scope

if TYPE_CHECKING:  # pragma: no cover
    from cq import MiddlewareResult

__all__ = ("InjectionScopeMiddleware",)


class InjectionScopeMiddleware:
    __slots__ = ("__scope_name",)

    __scope_name: str

    def __init__(self, scope_name: str) -> None:
        self.__scope_name = scope_name

    async def __call__(self, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        async with adefine_scope(self.__scope_name):
            yield
