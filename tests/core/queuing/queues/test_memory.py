import math
from typing import Any

import pytest
from anyio import ClosedResourceError

from cq import MemoryQueue, MiddlewareResult


async def _receive_all[T](queue: MemoryQueue[T]) -> list[T]:
    messages = []

    async for delivery in queue:
        async with delivery as message:
            messages.append(message)

    return messages


class TestMemoryQueue:
    async def test_aiter_with_success_yields_sent_messages(self) -> None:
        queue = MemoryQueue[str](math.inf)
        await queue.send("first")
        await queue.send("second")
        await queue.close()

        assert await _receive_all(queue) == ["first", "second"]

    async def test_call_with_success_sends_message(self) -> None:
        queue = MemoryQueue[str](math.inf)
        await queue("message")
        await queue.close()

        assert await _receive_all(queue) == ["message"]

    async def test_send_with_closed_queue_raises_closed_resource_error(self) -> None:
        queue = MemoryQueue[str]()
        await queue.close()

        with pytest.raises(ClosedResourceError):
            await queue.send("message")

    async def test_send_with_exited_queue_raises_closed_resource_error(self) -> None:
        async with MemoryQueue[str]() as queue:
            pass

        with pytest.raises(ClosedResourceError):
            await queue.send("message")

    async def test_draining_with_success_dispatches_sent_messages_then_closes_queue(
        self,
    ) -> None:
        dispatched = []

        async def dispatcher(message: str) -> None:
            dispatched.append(message)

        async with MemoryQueue[str]().draining(dispatcher) as queue:
            await queue.send("first")
            await queue.send("second")

        assert dispatched == ["first", "second"]

        with pytest.raises(ClosedResourceError):
            await queue.send("third")

    async def test_draining_with_middlewares_wraps_dispatcher(self) -> None:
        calls = []

        async def middleware(message: str) -> MiddlewareResult[Any]:
            calls.append(f"before {message}")
            yield
            calls.append(f"after {message}")

        async def dispatcher(message: str) -> None:
            calls.append(f"dispatch {message}")

        queue = MemoryQueue[str]()

        async with queue.draining(dispatcher, middlewares=[middleware]):
            await queue.send("message")

        assert calls == ["before message", "dispatch message", "after message"]

    async def test_draining_with_dispatcher_error_raises_exception_group(
        self,
    ) -> None:
        async def dispatcher(message: str) -> None:
            raise ValueError(message)

        queue = MemoryQueue[str]()

        with pytest.raises(ExceptionGroup) as exc_info:
            async with queue.draining(dispatcher):
                await queue.send("message")

        assert exc_info.group_contains(ValueError, match="message")

    async def test_draining_with_dispatcher_error_and_fail_silently_dispatches_next_messages(
        self,
    ) -> None:
        dispatched = []

        async def dispatcher(message: str) -> None:
            dispatched.append(message)
            raise ValueError(message)

        queue = MemoryQueue[str]()

        async with queue.draining(dispatcher, fail_silently=True):
            await queue.send("first")
            await queue.send("second")

        assert dispatched == ["first", "second"]
