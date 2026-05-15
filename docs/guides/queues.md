# Queueing messages

Some workloads benefit from putting a queue between the producer of a message and its dispatcher: smoothing bursts, isolating slow handlers from the request path, or simply detaching event publication from the lifecycle of the caller. **python-cq** ships two building blocks for that pattern: a `Queue` protocol and a `Pump` that drains it into any dispatcher.

## The `Queue` protocol

`Queue` is the combination of two protocols, kept separate so you can type producer-side and consumer-side ends independently:

* `Producer[T]` exposes `send(message)` and is callable.
* `Consumer[T]` exposes `__aiter__` and yields messages as they arrive.

Any object that satisfies these protocols can act as a queue. The library provides `MemoryQueue` as the default in-process implementation, and you are free to write your own without changing the rest of the API.

## `MemoryQueue`

`MemoryQueue` is a thin wrapper around `anyio.create_memory_object_stream`. It is bounded by an optional `maxsize`, in which case `send` waits until a slot is available.

```python
from cq import Command, MemoryQueue

queue: MemoryQueue[Command] = MemoryQueue(maxsize=100)
await queue.send(command)
```

`MemoryQueue` is the right tool when producer and consumer live in the same process. For cross-process or persistent queues, implement `Queue` against your transport of choice.

## Draining a queue with `Pump`

`Pump` connects a `Consumer` to a dispatcher. The dispatcher is any async callable that accepts one message; in practice this is usually a bus.

```python
from cq import Command, CommandBus, MemoryQueue, Pump
from typing import Any

command_bus: CommandBus[Any] = ...
queue: MemoryQueue[Command] = MemoryQueue()

async with Pump(queue, command_bus).draining():
    await queue.send(command)
```

While the `draining` context is open, a background task consumes the queue and forwards each message to the dispatcher. On exit, the task group is cancelled by default, which stops the pump immediately even if some messages are still in flight.

### Graceful shutdown

Pass `graceful=True` to let the pump finish draining whatever is already queued before the context exits. This relies on the queue being closed so the async iterator can terminate; otherwise the pump would wait forever for the next message.

```python
async with Pump(queue, command_bus).draining(graceful=True):
    await queue.send(command_1)
    await queue.send(command_2)
    await queue.close()
```

### Suppressing dispatcher errors

By default, an exception raised by the dispatcher stops the pump and propagates out of `draining`. Set `fail_silently=True` on the `Pump` if you want individual failures to be swallowed and the pump to keep consuming the rest of the queue:

```python
Pump(queue, command_bus, fail_silently=True)
```

Use this when each message is independent and a failed dispatch should not take down the whole consumer. Logging or alerting on failures is the dispatcher's responsibility, typically through a middleware on the underlying bus.

## `MemoryQueue.draining` shortcut

`MemoryQueue` exposes a `draining` helper that combines `Pump` with the queue's own lifecycle. It opens a pump, yields the queue, and closes it on exit so the pump terminates gracefully without an explicit `close` call:

```python
from cq import CommandBus, MemoryQueue
from injection import inject
from typing import Any

@inject
async def main(command_bus: CommandBus[Any]) -> None:
    async with MemoryQueue().draining(command_bus) as queue:
        await queue.send(command_1)
        await queue.send(command_2)
    # Both commands have been dispatched here.
```

`fail_silently` is forwarded to the underlying `Pump`.
