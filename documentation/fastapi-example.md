# [FastAPI](https://github.com/fastapi/fastapi) Example

The advantage of `python-cq` is that it can be easily integrated into FastAPI.

Here's an example of its integration:

```python
import msgspec
from cq import CommandBus, command_handler, new_command_bus
from fastapi import FastAPI, status
from injection import injectable, singleton
from injection.integrations.fastapi import Inject

# ----- Service Definition -----

@injectable
class ExampleService: ...

@singleton
def override_command_bus_recipe() -> CommandBus:
    bus = new_command_bus()
    bus.add_middlewares(...)  # Add middlewares here
    return bus

# ----- Command Definition -----

class ExampleCommand(msgspec.Struct, frozen=True): ...

class ExampleReturnType(msgspec.Struct, frozen=True): ...

@command_handler(ExampleCommand)
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
    command_bus: CommandBus[ExampleReturnType] = Inject(CommandBus),
) -> None:
    result = await command_bus.dispatch(command)
    # ...
```
