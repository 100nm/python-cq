# Pipeline

Pipelines are designed to execute several commands one after the other, while encapsulating them in middleware.

## Pipe

A simple pipeline implementation.

Example:

```python
from cq import AnyCommandBus, Pipe

async def pipeline_example(command_bus: AnyCommandBus) -> None:
    pipeline: Pipe[FirstCommand, ThirdResult] = Pipe(command_bus)
    pipeline.add_middlewares(...)  # You can add middleware to encapsulate the pipeline in a transaction, for example.

    @pipeline.step
    async def _(result: FirstResult) -> SecondCommand:
        """ Transform the return value into a new command. """

    @pipeline.step
    async def _(result: SecondResult) -> ThirdCommand:
        """ Transform the return value into a new command. """

    command = FirstCommand(...)
    output_value = await pipeline.dispatch(command)
    # ...
```

## ContextPipeline

A limitation of `Pipe` is that it isn't possible to have values that go through the steps. Each converter in a `Pipe` 
receives only the output of the previous one, but the intermediate state, any contextual information, is lost between 
steps.

This makes it impossible to accumulate data or share context between converters without resorting to global variables.

To solve this limitation, `ContextPipeline` introduces a contextual layer: each stage operates within the same instance,
allowing stateful processing and side effects to persist across the entire pipeline execution.

Example:

```python
from cq import ContextCommandPipeline, ContextPipeline

class ContextExample:
    user_id: int

    pipeline: ContextPipeline[FirstCommand] = ContextCommandPipeline()

    @pipeline.step
    async def _(self, result: FirstResult) -> SecondCommand:
        self.user_id = result.user_id  # set user_id in context
        return SecondCommand(...)

    @pipeline.step
    async def _(self, result: SecondResult) -> ThirdCommand:
        """ Transform the return value into a new command. """
        
    @pipeline.step
    async def _(self, result: ThirdResult) -> None:
        """ The last step is optional, but if you need it, you must return `None`. """

async def how_to_dispatch() -> None:
    command = FirstCommand(...)
    context = await ContextExample.pipeline.dispatch(command)
    # ...
```
