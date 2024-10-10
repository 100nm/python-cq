from typing import Any

import pytest

from cq import Bus
from cq._core.bus import SimpleBus
from tests.helpers.history import HistoryMiddleware


@pytest.fixture(scope="function")
def bus() -> Bus[Any, Any]:
    return SimpleBus()


@pytest.fixture(scope="function")
def history() -> HistoryMiddleware:
    return HistoryMiddleware()
