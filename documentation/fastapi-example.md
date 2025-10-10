# [FastAPI](https://github.com/fastapi/fastapi) Example

The advantage of `python-cq` is that it can be easily integrated into FastAPI.

Here's an example of its integration:

```python
from cq import CommandBus, command_handler, new_command_bus
from cq.ext.fastapi import DeferredCommandBus
from fastapi import FastAPI, status
from injection import injectable
from injection.ext.fastapi import Inject
from pydantic import BaseModel

# ----- Service Definition -----

@injectable
class ExampleService: ...

@injectable
def override_command_bus_recipe() -> CommandBus:
    bus = new_command_bus()
    bus.add_middlewares(...)  # Add middlewares here
    return bus

# ----- Command Definition -----

class ExampleCommand(BaseModel): ...

class ExampleReturnType: ...

@command_handler
class ExampleHandler:
    def __init__(self, service: ExampleService) -> None:
        self.service = service

    async def handle(self, command: ExampleCommand) -> ExampleReturnType: ...

# ----- FastAPI Setup -----

app = FastAPI()

# ----- FastAPI Endpoint -----

@app.post("/example", status_code=status.HTTP_204_NO_CONTENT)
async def example(
    command: ExampleCommand,
    command_bus: Inject[CommandBus[ExampleReturnType]],
) -> None:
    result = await command_bus.dispatch(command)
    # ...

@app.post("/background-example", status_code=status.HTTP_204_NO_CONTENT)
async def background_example(
    command: ExampleCommand,
    command_bus: DeferredCommandBus,
) -> None:
    # runs the command in the background
    # so the client receives a response more quickly
    # but isn't notified in case of error
    await command_bus.defer(command)
```
