# Configuring a bus

!!! note
    This guide assumes the `[injection]` extra is installed. If you use a different DI framework, register the factory below with your own container, not with `@injectable`.

Each bus can be customized by attaching listeners and middlewares. The recommended pattern is a factory function that builds a configured bus and registers it in the DI container:

```python
from cq import CommandBus, new_command_bus
from injection import injectable


async def listener(message): ...


async def middleware(message):
    # runs before the handler
    result = yield
    # runs after the handler


@injectable
def command_bus_factory() -> CommandBus:
    bus = new_command_bus()
    bus.add_listeners(listener)
    bus.add_middlewares(middleware)
    return bus
```

The same pattern applies to `QueryBus` and `EventBus`, with `new_query_bus()` and `new_event_bus()`.

## Listeners

Listeners are fire-and-forget callables that receive the message. They are useful for logging, metrics, or any side effect that does not need to influence the handler.

```python
async def log_listener(message):
    print(f"Received: {message}")
```

Listeners are scheduled in an `anyio` task group, so several listeners run concurrently. The timing depends on the bus type:

* **`CommandBus` and `QueryBus`**: every listener must finish before the handler runs. The handler cannot start until listeners have settled, and `dispatch` returns the handler's value as soon as it completes.
* **`EventBus`**: listeners and handlers share the same task group, so they all run concurrently. `dispatch` returns once everything has finished.

## Middlewares

A middleware wraps handler execution. Use it to run logic before and after the handler processes the message, or to handle exceptions.

```python
import time


async def timing_middleware(message):
    start = time.time()
    yield
    print(f"Execution time: {time.time() - start}s")
```

For commands and queries, the middleware stack wraps the single registered handler once. For events, the stack is applied around each handler independently, so a middleware sees one invocation per event handler.

The `yield` form makes the middleware look like a try/finally around the handler call. The expression `result = yield` receives the handler's return value, but only for inspection: middlewares of this form cannot replace it. This was a deliberate choice to keep the message and the result read-only by default.

### Classic middlewares

If you need to read or substitute the return value, write a "classic" middleware. It takes `call_next` as its first argument and returns the value it wants to expose to the caller:

```python
import time


async def timing_middleware(call_next, message):
    start = time.time()
    result = await call_next(message)
    print(f"Execution time: {time.time() - start}s")
    return result
```

Both styles can be mixed freely in the same bus.

## Class-based listeners and middlewares

Listeners and middlewares can also be classes with a `__call__` method, which is convenient when they need their own dependencies:

```python
from dataclasses import dataclass


@dataclass
class LogListener:
    logger: Logger

    async def __call__(self, message):
        self.logger.info(f"Received: {message}")


@dataclass
class TimingMiddleware:
    metrics: MetricsService

    async def __call__(self, message):
        start = time.time()
        yield
        await self.metrics.record(time.time() - start)


@dataclass
class ClassicTimingMiddleware:
    metrics: MetricsService

    async def __call__(self, call_next, message):
        start = time.time()
        result = await call_next(message)
        await self.metrics.record(time.time() - start)
        return result
```

If you build these classes through your DI container, you get the same constructor injection as for handlers.

## Built-in middlewares

### `RetryMiddleware`

`cq.middlewares.retry.RetryMiddleware` retries the wrapped call when it raises one of the configured exception types:

```python
from cq import new_command_bus
from cq.middlewares.retry import RetryMiddleware

bus = new_command_bus()
bus.add_middlewares(RetryMiddleware(retry=3, delay=0.5, exceptions=(TimeoutError,)))
```

The parameters are:

* `retry`: total number of attempts (including the first one). With `retry=3`, the call runs at most three times.
* `delay`: seconds to wait between attempts. Defaults to `0`.
* `exceptions`: the exception types that trigger a retry. Defaults to `(Exception,)`, which retries on any non-`BaseException` failure.

If every attempt fails, the last exception is re-raised.

### `CaptureExceptionMiddleware`

`cq.middlewares.exc.CaptureExceptionMiddleware` catches exceptions raised by downstream handlers and forwards them to a callback. Use it to log, report, or push errors to an external sink without changing how they propagate:

```python
from cq import new_command_bus
from cq.middlewares.exc import CaptureExceptionMiddleware


async def report(exception, message):
    sentry_sdk.capture_exception(exception)


bus = new_command_bus()
bus.add_middlewares(CaptureExceptionMiddleware(report, reraise=True))
```

The parameters are:

* `on_error`: an async callback invoked with the captured exception followed by the same arguments the handler received (typically the message). Use `CaptureExceptionMiddleware.sync(...)` if your callback is synchronous.
* `exceptions`: the exception types to capture. Defaults to `(Exception,)`.
* `reraise`: whether to re-raise the exception after the callback returns. Defaults to `False`, in which case the exception is swallowed.

`on_error` is meant for side effects only (logging, metrics, notifications) and must not raise. If it does, its own exception will propagate in place of the original one.
