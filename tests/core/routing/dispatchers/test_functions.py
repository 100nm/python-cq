from cq import dispatch_sequentially
from cq._core.routing.dispatchers.bus import SimpleBus


async def test_dispatch_sequentially_with_success_returns_results_in_order() -> None:
    dispatched = []

    async def handler(message: str) -> str:
        dispatched.append(message)
        return message.upper()

    bus = SimpleBus[str, str]().subscribe(str, handler)

    results: tuple[str, str] = await dispatch_sequentially(bus, "first", "second")

    assert results == ("FIRST", "SECOND")
    assert dispatched == ["first", "second"]


async def test_dispatch_sequentially_without_messages_returns_empty_tuple() -> None:
    bus = SimpleBus[str, str]()

    assert await dispatch_sequentially(bus) == ()
