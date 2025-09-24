from __future__ import annotations

from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from injection import adefine_scope
from injection.exceptions import ScopeAlreadyDefinedError

if TYPE_CHECKING:  # pragma: no cover
    from cq import MiddlewareResult

__all__ = ("InjectionScopeMiddleware",)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class InjectionScopeMiddleware:
    scope_name: str
    exist_ok: bool = field(default=False, kw_only=True)
    threadsafe: bool | None = field(default=None, kw_only=True)

    async def __call__(self, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        async with AsyncExitStack() as stack:
            cm = adefine_scope(self.scope_name, threadsafe=self.threadsafe)
            try:
                await stack.enter_async_context(cm)

            except ScopeAlreadyDefinedError:
                if not self.exist_ok:
                    raise

            del cm
            yield
