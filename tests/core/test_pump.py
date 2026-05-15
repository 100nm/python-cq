import anyio

from cq import MemoryQueue, Pump


class TestPump:
    async def test_draining_without_graceful(self) -> None:
        dispatched = anyio.Event()

        async def dispatcher(message: str) -> None:
            await anyio.sleep(60)
            dispatched.set()

        queue = MemoryQueue[str]()

        async with Pump(queue, dispatcher).draining(graceful=False):
            await queue.send("message")

        assert not dispatched.is_set()
