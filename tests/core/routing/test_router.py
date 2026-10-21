from typing import Any

from cq import ContextCommandPipeline, Router
from cq._core.routing.di import NoDI
from cq.ext.injection import InjectionAdapter


class _Message: ...


class TestRouter:
    def test_di_with_adapter_returns_adapter(self) -> None:
        adapter = InjectionAdapter()

        assert Router(adapter).di is adapter

    def test_di_without_adapter_returns_no_di(self) -> None:
        assert isinstance(Router().di, NoDI)

    def test_command_types_with_success_returns_command_handler_types(self) -> None:
        router = Router()

        @router.command_handler
        class Handler:
            async def handle(self, command: _Message) -> None: ...

        assert set(router.command_types) == {_Message}

    def test_event_types_with_success_returns_event_handler_types(self) -> None:
        router = Router()

        @router.event_handler
        class Handler:
            async def handle(self, event: _Message) -> None: ...

        assert set(router.event_types) == {_Message}

    def test_query_types_with_success_returns_query_handler_types(self) -> None:
        router = Router()

        @router.query_handler
        class Handler:
            async def handle(self, query: _Message) -> None: ...

        assert set(router.query_types) == {_Message}

    def test_command_pipeline_with_success_returns_context_command_pipeline(
        self,
    ) -> None:
        pipeline: ContextCommandPipeline[Any] = Router(
            InjectionAdapter(),
        ).command_pipeline()

        assert isinstance(pipeline, ContextCommandPipeline)

    async def test_new_command_bus_with_success_returns_bus_dispatching_to_command_handler(
        self,
    ) -> None:
        router = Router()

        @router.command_handler
        class Handler:
            async def handle(self, command: _Message) -> str:
                return "command handled"

        bus = router.new_command_bus()

        assert await bus.dispatch(_Message()) == "command handled"

    async def test_new_event_bus_with_success_returns_bus_dispatching_to_event_handlers(
        self,
    ) -> None:
        router = Router()
        handled: list[Any] = []

        @router.event_handler
        class FirstHandler:
            async def handle(self, event: _Message) -> None:
                handled.append(type(self))

        @router.event_handler
        class SecondHandler:
            async def handle(self, event: _Message) -> None:
                handled.append(type(self))

        bus = router.new_event_bus()
        await bus.dispatch(_Message())

        assert set(handled) == {FirstHandler, SecondHandler}

    async def test_new_query_bus_with_success_returns_bus_dispatching_to_query_handler(
        self,
    ) -> None:
        router = Router()

        @router.query_handler
        class Handler:
            async def handle(self, query: _Message) -> str:
                return "query handled"

        bus = router.new_query_bus()

        assert await bus.dispatch(_Message()) == "query handled"

    def test_register_defaults_with_success_returns_self(self) -> None:
        router = Router()

        assert router.register_defaults() is router
