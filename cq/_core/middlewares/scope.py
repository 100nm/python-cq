from dataclasses import dataclass
from typing import Any

from cq._core.di import DIAdapter
from cq._core.middleware import MiddlewareResult


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class CommandDispatchScopeMiddleware:
    di: DIAdapter

    async def __call__(self, /, *args: Any, **kwargs: Any) -> MiddlewareResult[Any]:
        async with self.di.command_scope():
            yield
