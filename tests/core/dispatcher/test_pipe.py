from typing import Any

from cq import Bus, Pipe
from cq._core.dispatcher.bus import SimpleBus


class TestPipe:
    async def test_dispatch_with_success_return_any(self, bus: Bus[Any, Any]) -> None:
        class StringLengthHandler:
            async def handle(self, input_value: str) -> int:
                return len(input_value)

        class UniformStringHandler:
            def __init__(self, char: str) -> None:
                self.char = char

            async def handle(self, input_value: int) -> str:
                return self.char * input_value

        class ToTupleHandler:
            async def handle(self, input_value: str) -> tuple[str, ...]:
                return tuple(input_value)

        bus.subscribe(str, StringLengthHandler)
        bus.subscribe(int, lambda: UniformStringHandler("*"))

        pipe: Pipe[str, str | tuple[str, ...]] = Pipe(bus)

        @pipe.step
        async def step_converter_1(length: int) -> int:
            return length

        assert await pipe.dispatch("hello") == "*****"

        other_bus: Bus[Any, Any] = SimpleBus()

        other_bus.subscribe(str, ToTupleHandler)

        @pipe.step(dispatcher=other_bus)
        async def step_converter_2(hidden_string: str) -> str:
            return hidden_string

        assert await pipe.dispatch("hello") == ("*", "*", "*", "*", "*")
