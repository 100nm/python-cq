# Pump

`Pump` connects a `Consumer` to a dispatcher. The dispatcher is any async callable that accepts one message: a bus, a function, or another queue's producer.

```python
from cq import EventBus, MemoryQueue, Pump

event_bus: EventBus = ...
queue: MemoryQueue[UserCreatedEvent] = MemoryQueue()

async with Pump(queue, event_bus).draining():
    # ...
    await queue.send(UserCreatedEvent(user_id=42))
```

While the `draining` context is open, a background task consumes the queue and passes each message to the dispatcher. On exit, the task is cancelled by default, which stops the pump right away even if some messages are still in flight.

`Pump` has no error policy of its own. Failures of the processing are the dispatcher's business (retries, dead letters, logging), and failures of the transport are the queue's.

## Graceful shutdown

Pass `graceful=True` to let the pump finish what is already queued before the context exits. The pump stops once the consumer's iteration ends, so the queue must be closed, otherwise the context waits forever for the next message:

```python
async with Pump(queue, event_bus).draining(graceful=True):
    # ...
    await queue.send(event_1)
    await queue.send(event_2)
    # ...
    await queue.close()
```

## `MemoryQueue.draining`

For a `MemoryQueue`, `draining` combines both steps: it opens a graceful pump, yields the queue, and closes it on exit, so the queue cannot be reused afterwards. When the block ends, every message sent inside it has been processed:

```python
from cq import MemoryQueue

async with MemoryQueue().draining(event_bus) as queue:
    # ...
    await queue.send(event_1)
    await queue.send(event_2)

# Both events have been dispatched here.
```

`concurrency`, `fail_silently`, and `middlewares` are forwarded to the underlying `Pump`.

## Errors

By default, an exception raised while processing a message stops the pump, cancels the code running inside the `draining` block, and propagates out of `draining`, inside an `ExceptionGroup` since the pump runs in a task group. Set `fail_silently=True` to swallow individual failures and keep consuming the rest of the queue:

```python
Pump(queue, event_bus, fail_silently=True)
```

Use it when each message is independent and one failed dispatch must not take the whole consumer down. Reporting the failures is the dispatcher's job, typically through a middleware on the bus.

The delivery sees the exception either way, so a queue can still reject the message before the pump moves on.

## Concurrency

A single drain loop pulls and dispatches messages one at a time, so the pump paces itself on the dispatcher's speed. Pass `concurrency=N` to `draining` to run `N` drain loops against the same consumer:

```python
async with Pump(queue, event_bus).draining(concurrency=4):
    # ...
```

The consumer must support concurrent iteration. `MemoryQueue` does, since it wraps an `anyio` memory stream; if you write your own, make sure its `__aiter__` can be consumed from several tasks at once.

Ordering is no longer guaranteed with `concurrency > 1`: a fast dispatch overtakes a slow one even if the queue delivers messages in order.

## Middlewares

A `Pump` has its own middleware stack, added with `add_middlewares`. A middleware wraps the processing of each message. It is either an async generator that yields where the dispatcher runs, or a function that takes `call_next` first and calls it:

```python
async def sentry_middleware(message):
    try:
        yield
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        raise


async def timing_middleware(call_next, message):
    start = time.perf_counter()
    result = await call_next(message)
    print(f"Processed in {time.perf_counter() - start}s")
    return result


pump = Pump(queue, event_bus).add_middlewares(sentry_middleware, timing_middleware)
```

These are the same middlewares as on a bus, so everything described in the [routing middlewares guide](../routing/middlewares.md) applies, including the built-in ones and the execution order. The exception is `resolve_handler_source`, which needs a handler behind `call_next` and therefore only works on a bus.

When the dispatcher is a bus, both stacks apply. Put each concern where it belongs:

* **On the pump**: what is tied to the consumption cycle, such as reporting failures that escape the dispatcher.
* **On the bus**: what is tied to handling the message, such as validation, business retries, or transactional boundaries.

`fail_silently=True` also swallows exceptions raised by a pump middleware, so a middleware that means to stop the pump is suppressed in that mode.
