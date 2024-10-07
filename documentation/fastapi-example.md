# [FastAPI](https://github.com/fastapi/fastapi) Example

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from cq import Command, CommandBus, command_handler, find_command_bus
from fastapi import FastAPI, status
from injection import injectable
from injection.integrations.fastapi import Inject

# ----- Service Definition -----

@injectable
class ExampleService: ...

# ----- Command Definition -----

class ExampleCommand(Command): ...

type HandlerReturnType = ...

@command_handler(ExampleCommand)
class ExampleHandler:
    def __init__(self, service: ExampleService) -> None:
        self.service = service

    async def handle(self, command: ExampleCommand) -> HandlerReturnType: ...

# ----- FastAPI Setup -----

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    find_command_bus().add_middlewares(...)  # Add middlewares here
    yield

app = FastAPI(lifespan=lifespan)

# ----- FastAPI Endpoint -----

@app.post("/example", status_code=status.HTTP_204_NO_CONTENT)
async def example(
    command: ExampleCommand,
    command_bus: CommandBus[HandlerReturnType] = Inject(CommandBus),
) -> None:
    result = await command_bus.dispatch(command)
```
