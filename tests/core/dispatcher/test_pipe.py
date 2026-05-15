from typing import Any, Self

from cq import Bus, Pipe
from cq._core.dispatchers.bus import SimpleBus


class TestPipe:
    async def test_dispatch_with_success_return_any(self, bus: Bus[Any, Any]) -> None:
        class StringLengthHandler:
            async def handle(self, input_value: str) -> int:
                return len(input_value)

            @classmethod
            async def async_factory(cls) -> Self:
                return cls()

        class UniformStringHandler:
            def __init__(self, char: str) -> None:
                self.char = char

            async def handle(self, input_value: int) -> str:
                return self.char * input_value

            @classmethod
            async def async_factory(cls, char: str) -> Self:
                return cls(char)

        class ToTupleHandler:
            async def handle(self, input_value: str) -> tuple[str, ...]:
                return tuple(input_value)

            @classmethod
            async def async_factory(cls) -> Self:
                return cls()

        bus.subscribe(str, StringLengthHandler.async_factory)
        bus.subscribe(int, lambda: UniformStringHandler.async_factory("*"))

        pipe: Pipe[str, str | tuple[str, ...]] = Pipe(bus)

        @pipe.step
        def step_converter_1(length: int) -> int:
            return length

        assert await pipe.dispatch("hello") == "*****"

        # Custom dispatcher
        other_bus: Bus[Any, Any] = SimpleBus()

        other_bus.subscribe(str, ToTupleHandler.async_factory)

        @pipe.step(dispatcher=other_bus)
        async def step_converter_2(hidden_string: str) -> str:
            return hidden_string

        assert await pipe.dispatch("hello") == ("*", "*", "*", "*", "*")

        # Add static step
        pipe.add_static_step(2)

        assert await pipe.dispatch("hello") == "**"
