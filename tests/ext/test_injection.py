from typing import Any

import pytest
from injection import Module
from injection.exceptions import ScopeAlreadyDefinedError

from cq import (
    AnyCommandBus,
    Bus,
    EventBus,
    QueryBus,
    RelatedEvents,
    Router,
)
from cq._core.middleware import MiddlewareGroup
from cq.ext.injection import InjectionAdapter, InjectionScopeMiddleware


class _Service: ...


class _Command: ...


class _Event: ...


class TestInjectionAdapter:
    async def test_lazy_with_success_returns_resolver_of_registered_instance(
        self,
        injection_module: Module,
    ) -> None:
        service = _Service()
        injection_module.set_constant(service)

        resolve = InjectionAdapter(injection_module).lazy(_Service)

        assert await resolve() is service

    async def test_wire_with_success_returns_factory_injecting_dependencies(
        self,
        injection_module: Module,
    ) -> None:
        service = _Service()
        injection_module.set_constant(service)

        class Handler:
            def __init__(self, service: _Service) -> None:
                self.service = service

        factory = InjectionAdapter(injection_module).wire(Handler)
        handler = await factory()

        assert handler.service is service

    def test_register_defaults_with_success_registers_buses(
        self,
        injection_module: Module,
    ) -> None:
        router = Router(InjectionAdapter(injection_module))

        router.register_defaults()

        for bus_type in (AnyCommandBus, EventBus, QueryBus[Any]):
            assert isinstance(injection_module.find_instance(bus_type), Bus)

    async def test_command_scope_with_success_provides_related_events_to_command_handlers(
        self,
        router: Router,
        injection_module: Module,
    ) -> None:
        handled_events = []

        @router.event_handler
        class EventHandler:
            async def handle(self, event: _Event) -> None:
                handled_events.append(event)

        @router.command_handler
        class CommandHandler:
            def __init__(self, related_events: RelatedEvents) -> None:
                self.related_events = related_events

            async def handle(self, command: _Command) -> None:
                self.related_events.add(_Event())

        command_bus = injection_module.find_instance(AnyCommandBus)
        await command_bus.dispatch(_Command())

        assert len(handled_events) == 1
        assert isinstance(handled_events[0], _Event)


class TestInjectionScopeMiddleware:
    async def test_call_with_scope_already_defined_raises_scope_already_defined_error(
        self,
    ) -> None:
        middleware = InjectionScopeMiddleware("__test_already_defined__")
        group = MiddlewareGroup[[], None]().add(middleware, middleware)

        async def handler() -> None: ...

        with pytest.raises(ScopeAlreadyDefinedError):
            await group.invoke(handler)

    async def test_call_with_scope_already_defined_and_exist_ok_calls_handler(
        self,
    ) -> None:
        handled = []
        scope_name = "__test_exist_ok__"
        group = MiddlewareGroup[[], None]().add(
            InjectionScopeMiddleware(scope_name),
            InjectionScopeMiddleware(scope_name, exist_ok=True),
        )

        async def handler() -> None:
            handled.append(True)

        await group.invoke(handler)

        assert handled == [True]
