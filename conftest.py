from typing import Any

import pytest
from injection import Module

from cq import Bus, CommandBus, EventBus, QueryBus, Router
from cq._core.routing.dispatchers.bus import SimpleBus
from cq.ext.injection import InjectionAdapter
from tests.helpers.history import HistoryMiddleware


@pytest.fixture(scope="function")
def router(injection_module: Module) -> Router:
    return Router(InjectionAdapter(injection_module)).register_defaults()


@pytest.fixture(scope="function")
def bus() -> Bus[Any, Any]:
    return SimpleBus()


@pytest.fixture(scope="function", autouse=True)
def ensure_test_dependencies(
    router: Router,
    history: HistoryMiddleware,
    injection_module: Module,
) -> None:
    injection_module.injectable(
        lambda: router.new_command_bus().add_middlewares(history),
        on=CommandBus,
    )
    injection_module.injectable(
        lambda: router.new_event_bus().add_middlewares(history),
        on=EventBus,
    )
    injection_module.injectable(
        lambda: router.new_query_bus().add_middlewares(history),
        on=QueryBus,
    )


@pytest.fixture(scope="function")
def history() -> HistoryMiddleware:
    return HistoryMiddleware()


@pytest.fixture(scope="function")
def injection_module() -> Module:
    return Module()
