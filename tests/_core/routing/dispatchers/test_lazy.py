from typing import Any

from injection import Module

from cq import QueryBus, Router
from cq._core.routing.dispatchers.lazy import LazyDispatcher
from cq.ext.injection import InjectionAdapter


class _Query: ...


class TestLazyDispatcher:
    async def test_dispatch_with_dispatcher_registered_after_creation_returns_result(
        self,
        injection_module: Module,
    ) -> None:
        router = Router(InjectionAdapter(injection_module))

        @router.query_handler
        class Handler:
            async def handle(self, query: _Query) -> str:
                return "query handled"

        dispatcher = LazyDispatcher[_Query, Any](QueryBus, router.di)
        router.register_defaults()

        assert await dispatcher.dispatch(_Query()) == "query handled"
