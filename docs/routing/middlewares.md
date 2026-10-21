# Middlewares

A middleware wraps the execution of a handler. Use it to run logic before and after the handler processes the message, or to deal with its exceptions. Middlewares are added to a bus with `add_middlewares`:

```python
bus = new_command_bus()
bus.add_middlewares(timing_middleware, transaction_middleware)
```

For commands and queries, the middleware stack wraps the single handler once. For events, the stack is applied around each handler independently, so a middleware sees one invocation per event handler.

The same middlewares can be attached to a [command pipeline](multiple_commands.md#middlewares) and to a [`Pump`](../queuing/pump.md#middlewares).

## Generator middlewares

The simplest form is an async generator that receives the message and yields once, where the handler should run:

```python
import time


async def timing_middleware(message):
    start = time.perf_counter()
    yield
    print(f"Execution time: {time.perf_counter() - start}s")
```

The `yield` behaves like a try/finally around the handler call. An exception raised by the handler is thrown at the `yield`, so you can catch it there:

```python
async def logging_middleware(message):
    try:
        yield
    except Exception:
        logger.exception("Failed to handle %r", message)
        raise
```

`result = yield` receives the handler's return value, but only for inspection: a generator middleware cannot replace it. This keeps the message and the result read-only by default. If the middleware swallows an exception instead of re-raising it, `dispatch` returns the `NotImplemented` sentinel.

After an exception, the middleware may `yield` again to call the handler one more time. This is how `RetryMiddleware` is written. Yielding again after a successful call raises `cq.exceptions.MiddlewareError`.

The return annotation for these middlewares is `MiddlewareResult[T]`, where `T` is the handler's return type:

```python
from cq import MiddlewareResult


async def timing_middleware(message: Any) -> MiddlewareResult[Any]:
    ...
    yield
```

## Classic middlewares

When you need to replace the return value, or decide whether the handler runs at all, write a "classic" middleware. It takes `call_next` as its first argument and returns the value it wants to expose to the caller:

```python
async def cache_middleware(call_next, query):
    if (cached := cache.get(query)) is not None:
        return cached

    result = await call_next(query)
    cache.set(query, result)
    return result
```

Both styles can be mixed freely on the same bus. `Middleware` is the type alias that covers both.

### Finding the handler

`resolve_handler_source(call_next)` returns the handler class behind `call_next`, so a classic middleware on a bus can read metadata from it, such as a class attribute or a marker set by your own decorator:

```python
from cq import resolve_handler_source


async def permission_middleware(call_next, message):
    handler_type = resolve_handler_source(call_next)
    check_permissions(getattr(handler_type, "required_permissions", ()))
    return await call_next(message)
```

## Class-based middlewares

Both styles can also be written as a class with an async `__call__` method, which is convenient when the middleware needs its own dependencies:

```python
from dataclasses import dataclass


@dataclass
class TimingMiddleware:
    metrics: MetricsService

    async def __call__(self, message):
        start = time.perf_counter()
        yield
        await self.metrics.record(time.perf_counter() - start)


@dataclass
class CacheMiddleware:
    cache: Cache

    async def __call__(self, call_next, query):
        ...
```

If you build these classes through your DI container (for example as parameters of the bus factory), you get the same constructor injection as for handlers.

## Execution order

Middlewares nest around the handler like the layers of an onion. Within one call, they run in the order you list them: the first argument is the outermost layer, so it starts first and finishes last.

```python
bus.add_middlewares(outer, inner)
# outer -> inner -> handler -> inner -> outer
```

Each subsequent call wraps whatever is already registered, so the middlewares added last end up outermost:

```python
bus.add_middlewares(a, b)  # a -> b -> handler
bus.add_middlewares(c)  # c -> a -> b -> handler
```

The rule also covers the command scope that `new_command_bus()` installs before you add anything. Your own middlewares sit outside of it: they wrap the dispatch of every related event, but they cannot inject a dependency that only exists inside the scope, such as `RelatedEvents`.

## Built-in middlewares

### `RetryMiddleware`

`cq.middlewares.retry.RetryMiddleware` calls the handler again when it raises one of the configured exception types:

```python
from cq.middlewares.retry import RetryMiddleware

bus.add_middlewares(RetryMiddleware(retry=3, delay=0.5, exceptions=(TimeoutError,)))
```

* `retry`: total number of attempts, including the first one. With `retry=3`, the handler runs at most three times. Must be at least `1`.
* `delay`: seconds to wait between attempts. Defaults to `0`.
* `exceptions`: the exception types that trigger a retry. Defaults to `(Exception,)`.

If every attempt fails, the last exception is re-raised.

### `CaptureExceptionMiddleware`

`cq.middlewares.exc.CaptureExceptionMiddleware` catches exceptions raised downstream and forwards them to a callback. Use it to log, report, or push errors to an external sink:

```python
from cq.middlewares.exc import CaptureExceptionMiddleware


async def report(exception, message):
    sentry_sdk.capture_exception(exception)


bus.add_middlewares(CaptureExceptionMiddleware(report, reraise=True))
```

* `on_error`: an async callback invoked with the captured exception followed by the arguments the handler received (the message). Use `CaptureExceptionMiddleware.sync(...)` if your callback is synchronous.
* `exceptions`: the exception types to capture. Defaults to `(Exception,)`.
* `reraise`: whether to re-raise the exception after the callback returns. Defaults to `False`, in which case the exception is swallowed.

`on_error` is meant for side effects only and must not raise. If it does, its own exception propagates in place of the original one.

### Context manager middlewares

`cq.middlewares.contextlib` turns an existing context manager into a middleware that wraps every dispatch:

* `ContextManagerMiddleware(context)` for a synchronous context manager;
* `AsyncContextManagerMiddleware(context)` for an asynchronous one.

```python
from contextlib import suppress
from cq.middlewares.contextlib import ContextManagerMiddleware

bus.add_middlewares(ContextManagerMiddleware(suppress(LookupError)))
```

The same context manager instance is entered on every dispatch, so it must be reusable. Context managers built with `@contextmanager` are single-use and do not fit here.
