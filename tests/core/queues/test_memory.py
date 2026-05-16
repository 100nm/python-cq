from dataclasses import dataclass, field

import pytest
from anyio import ClosedResourceError

from cq import MemoryQueue


class TestMemoryQueue:
    async def test_draining_with_success(self) -> None:
        history = _History[str]()

        async with MemoryQueue[str]().draining(history) as queue:
            await queue.send("message_1")
            await queue.send("message_2")

        with pytest.raises(ClosedResourceError):
            await queue.send("message_3")

        assert len(history) == 2

    async def test_draining_with_fail_silently(self) -> None:
        async def dispatcher(message: str) -> None:
            raise NotImplementedError

        async with MemoryQueue[str]().draining(dispatcher, fail_silently=True) as queue:
            await queue.send("message_1")
            await queue.send("message_2")

    async def test_draining_without_fail_silently(self) -> None:
        async def dispatcher(message: str) -> None:
            raise NotImplementedError

        with pytest.raises(ExceptionGroup):
            async with MemoryQueue[str]().draining(
                dispatcher,
                fail_silently=False,
            ) as queue:
                await queue.send("message")


@dataclass
class _History[T]:
    __records: list[T] = field(default_factory=list, init=False)

    async def __call__(self, message: T) -> None:
        self.__records.append(message)

    def __len__(self) -> int:
        return len(self.__records)
