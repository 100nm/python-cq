from typing import Any, Self

from cq import Bus, dispatch_sequentially


async def test_dispatch_sequentially_with_success_return_tuple(
    bus: Bus[Any, Any],
) -> None:
    class Handler:
        async def handle(self, message: str) -> str:
            return message

        @classmethod
        async def async_factory(cls) -> Self:
            return cls()

    bus.subscribe(str, Handler.async_factory)

    messages = ("a", "b")
    results: tuple[str, str] = await dispatch_sequentially(bus, *messages)
    assert messages == results
