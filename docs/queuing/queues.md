# Queues

Some workloads benefit from a queue between the code that produces a message and the code that processes it: smoothing bursts, keeping slow work out of the request path, or detaching the processing from the lifecycle of the caller. **python-cq** ships two building blocks for that:

* a `Queue` protocol, with `MemoryQueue` as the in-process implementation;
* a [`Pump`](pump.md) that drains a queue into any async callable.

Neither depends on the routing part of the library. A message can be any object, and the dispatcher on the other end can be a bus, a plain function, or anything else that accepts one message.

## The `Queue` protocol

`Queue[T]` combines two protocols, kept separate so the producer side and the consumer side can be typed independently:

* `Producer[T]` exposes `async send(message)`. It is also callable, so `await producer(message)` is the same as `await producer.send(message)`.
* `Consumer[T]` is async iterable and yields a `Delivery[T]` for each incoming message.

A `Delivery[T]` is an async context manager around a single message. Entering it gives the message, and leaving it tells the queue that processing is over, with or without an exception. This is where a transport-specific queue plugs its acknowledgement or requeue logic. `Pump` handles the delivery lifecycle, so application code rarely touches `Delivery` directly.

Any object that satisfies these protocols can be used as a queue.

!!! note
    If you'd like a `Queue` implementation for a specific library, feel free to open a [discussion on GitHub](https://github.com/100nm/python-cq/discussions).

## `MemoryQueue`

`MemoryQueue` is a thin wrapper around `anyio.create_memory_object_stream`. `maxsize` is how many messages the queue buffers before `send` waits for a free slot:

```python
from cq import MemoryQueue

queue: MemoryQueue[UserCreatedEvent] = MemoryQueue(maxsize=100)
await queue.send(UserCreatedEvent(user_id=42))
```

The default, `maxsize=0`, means no buffer at all: `send` waits until a consumer takes the message. It keeps the producer from running ahead of the consumer, but `await queue.send(...)` blocks forever if nothing is draining the queue. Send from inside a draining context (see [Pump](pump.md)), or pass `maxsize=math.inf` for an unbounded buffer.

`close()` stops the queue: consumers finish the messages already buffered, then their iteration ends. `MemoryQueue` is also an async context manager that closes itself on exit.

`MemoryQueue` fits when producer and consumer live in the same process. It is not thread-safe: `send` and the consumption must run on the event loop that created the queue. For cross-process or persistent queues, implement `Queue` against your transport.

## Writing your own queue

A custom queue implements `send` and `__aiter__`. Subclassing `Queue` gives you the callable behavior of `Producer` for free. The delivery is the place for acknowledgement: acknowledge when the processing succeeds, reject when it raises.

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from cq import Delivery, Queue


class BrokerQueue[T](Queue[T]):
    def __init__(self, client: BrokerClient, topic: str) -> None:
        self.client = client
        self.topic = topic

    async def send(self, message: T, /) -> None:
        await self.client.publish(self.topic, encode(message))

    async def __aiter__(self) -> AsyncIterator[Delivery[T]]:
        async for record in self.client.subscribe(self.topic):
            yield self.__deliver(record)

    @asynccontextmanager
    async def __deliver(self, record: Record) -> AsyncIterator[T]:
        try:
            yield decode(record.payload)
        except Exception:
            await record.reject()
            raise
        else:
            await record.ack()
```

`BrokerClient`, `Record`, `encode`, and `decode` stand for whatever your transport library provides. The message itself stays plain data: transport concerns live in the queue, not on the message.

The resilience of the transport (reconnecting, retrying a failed fetch) also belongs to the queue. If the iteration raises, the pump draining it stops.
