# Configuring a bus

!!! note
    This guide assumes the `[injection]` extra is installed. If you use a different DI framework, register the factories below with your own container instead of `@injectable`.

The buses resolved by default have no listeners and no middlewares. To customize one, write a factory that builds the bus with `new_command_bus()`, `new_query_bus()`, or `new_event_bus()`, configures it, and registers it in the DI container:

```python
from cq import CommandBus, new_command_bus
from injection import injectable


@injectable
def command_bus_factory() -> CommandBus:
    bus = new_command_bus()
    bus.add_listeners(log_listener)
    bus.add_middlewares(timing_middleware)
    return bus
```

Your factory takes precedence over the default registration, so every handler, middleware, or function that depends on `CommandBus` now receives the configured bus. The same pattern applies to `QueryBus` and `EventBus`.

`new_command_bus()` returns a bus that already wraps each dispatch in the command scope of the DI adapter. Always start from it rather than building a bus by hand, or `RelatedEvents` will not be available to your command handlers.

Both `add_listeners` and `add_middlewares` accept any number of arguments and return the bus, so calls can be chained.

## Listeners

A listener is an async callable that receives the message. Its return value is ignored. Listeners suit logging, metrics, or any side effect that does not need to influence the handler:

```python
async def log_listener(message):
    print(f"Received: {message}")
```

Listeners are scheduled in an `anyio` task group, so several listeners run concurrently. The timing depends on the bus type:

* **`CommandBus` and `QueryBus`**: every listener must finish before the handler runs. `dispatch` then returns the handler's value as soon as it completes.
* **`EventBus`**: listeners and handlers share the same task group, so they all run concurrently. `dispatch` returns once everything has finished.

A listener is not isolated from the dispatch. An exception raised by a listener escapes `dispatch` inside an `ExceptionGroup`, and on a `CommandBus` or a `QueryBus` this happens before the handler is called, so the message is never handled. Guard fragile listener code with its own try/except if it must not affect the dispatch.

A listener can also be a class with an async `__call__` method, which is convenient when it needs its own dependencies:

```python
from dataclasses import dataclass


@dataclass
class LogListener:
    logger: Logger

    async def __call__(self, message):
        self.logger.info(f"Received: {message}")
```

## Middlewares

Middlewares wrap the execution of the handler, to run logic before and after it or to deal with its exceptions. They have their own page: [Middlewares](middlewares.md).
