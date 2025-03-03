# Pipeline

Pipelines are designed to execute several commands one after the other, while encapsulating them in middleware.

Example:

```python
from cq import AnyCommandBus, Pipe

async def pipeline_example(command_bus: AnyCommandBus) -> None:
    pipeline: Pipe[FirstCommand, ThirdResult] = Pipe(command_bus)
    pipeline.add_middlewares(...)  # You can add middleware to encapsulate the pipeline in a transaction, for example.

    @pipeline.step
    async def converter_1(output_value: FirstResult) -> SecondCommand:
        """ Transform the return value into a new command. """

    @pipeline.step
    async def converter_2(output_value: SecondResult) -> ThirdCommand:
        """ Transform the return value into a new command. """

    command = FirstCommand(...)
    output_value = await pipeline.dispatch(command)
    # ...
```
