from collections.abc import Iterator
from typing import Any

import pytest
from injection.testing import load_test_profile, set_test_constant

from cq import (
    Bus,
    CommandBus,
    EventBus,
    QueryBus,
    new_command_bus,
    new_event_bus,
    new_query_bus,
)
from cq._core.dispatcher.bus import SimpleBus
from tests.helpers.history import HistoryMiddleware


@pytest.fixture(scope="function")
def bus() -> Bus[Any, Any]:
    return SimpleBus()


@pytest.fixture(scope="function")
def history() -> HistoryMiddleware:
    return HistoryMiddleware()


@pytest.fixture(scope="function", autouse=True)
def ensure_test_dependencies(history: HistoryMiddleware) -> Iterator[None]:
    command_bus: CommandBus[Any] = new_command_bus().add_middlewares(history)
    event_bus: EventBus = new_event_bus().add_middlewares(history)
    query_bus: QueryBus[Any] = new_query_bus().add_middlewares(history)

    set_test_constant(command_bus, on=CommandBus, alias=True, mode="override")
    set_test_constant(event_bus, on=EventBus, alias=True, mode="override")
    set_test_constant(query_bus, on=QueryBus, alias=True, mode="override")

    with load_test_profile():
        yield
