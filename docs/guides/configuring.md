# Configuring a Bus

Each bus can be customized with listeners and middlewares. To do so, create a factory function decorated with `@injectable` that returns the configured bus.
```python
from cq import CommandBus, MiddlewareResult, new_command_bus
from injection import injectable

async def listener(message: MessageType):
    ...

async def middleware(message: MessageType) -> MiddlewareResult[ReturnType]:
    # do something before the handler is executed
    return_value = yield
    # do something after the handler is executed

@injectable
def command_bus_factory() -> CommandBus:
    bus = new_command_bus()
    bus.add_listeners(listener)
    bus.add_middlewares(middleware)
    return bus
```

The same pattern applies to `QueryBus` and `EventBus` using `new_query_bus()` and `new_event_bus()`.

## Listeners

Listeners are executed before the handler(s). They receive the message and can perform side effects such as logging or validation.
```python
async def log_listener(message: MessageType):
    print(f"Received: {message}")
```

## Middlewares

Middlewares wrap around handler execution, allowing you to run logic before and after a handler processes a message.
```python
async def timing_middleware(message: Any) -> MiddlewareResult[Any]:
    start = time.time()
    yield
    print(f"Execution time: {time.time() - start}s")
```

For commands and queries, middlewares run once around the single handler. For events, middlewares run around each handler individually.

!!! note
    The generator was chosen to keep both the input message and the return value read-only.

## Class-based listeners and middlewares

For more flexibility, listeners and middlewares can be defined as classes with a `__call__` method. This allows you to inject dependencies and configure their behavior.
```python
from cq import MiddlewareResult
from dataclasses import dataclass

@dataclass
class LogListener:
    logger: Logger

    async def __call__(self, message: Any):
        self.logger.info(f"Received: {message}")

@dataclass
class TimingMiddleware:
    metrics: MetricsService

    async def __call__(self, message: Any) -> MiddlewareResult[Any]:
        start = time.time()
        yield
        self.metrics.record(time.time() - start)
```