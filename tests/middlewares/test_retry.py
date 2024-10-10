from typing import Any

import pytest

from cq import Bus
from cq.middlewares.retry import RetryMiddleware
from tests.helpers.history import HistoryMiddleware


class TestRetryMiddleware:
    async def test_retry_middleware_with_success(
        self,
        bus: Bus[Any, Any],
        history: HistoryMiddleware,
    ) -> None:
        class SomeHandler:
            async def handle(self, input_value: str) -> str:
                return input_value

        bus.add_middlewares(
            RetryMiddleware(3),
            history,
        ).subscribe(
            str,
            SomeHandler,
        )

        await bus.dispatch("Hello world!")
        assert len(history.records) == 1

    async def test_retry_middleware_with_retry(
        self,
        bus: Bus[Any, Any],
        history: HistoryMiddleware,
    ) -> None:
        class SomeHandler:
            async def handle(self, input_value: str) -> None:
                raise ValueError(input_value)

        retry = 3
        bus.add_middlewares(
            RetryMiddleware(retry),
            history,
        ).subscribe(
            str,
            SomeHandler,
        )

        with pytest.raises(ValueError):
            await bus.dispatch("Hello world!")

        assert len(history.records) == retry
