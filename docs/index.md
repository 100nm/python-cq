# python-cq

[![PyPI - Version](https://shieldcn.dev/pypi/v/python-cq.svg?variant=secondary)](https://pypi.org/project/python-cq)
[![PyPI - Downloads](https://shieldcn.dev/pypi/dm/python-cq.svg?variant=secondary)](https://pypistats.org/packages/python-cq)

**python-cq** is an async-first Python library for organizing code around CQRS. It routes commands, queries, and events to their handlers through dedicated buses, and lets you put a queue in front of any of them when a message should be processed later. Dependency injection is pluggable behind a small protocol.

The library is made of two independent parts:

* **Routing**: messages, handlers, buses, middlewares, and command pipelines. This is the core of the library and what most applications need.
* **Queuing**: a `Queue` protocol and a `Pump` that drains a queue into any async callable, typically a bus.

You can use routing without ever touching queuing, and the queuing primitives work with any dispatcher, not only the buses of this library.

## What is CQRS?

CQRS (Command Query Responsibility Segregation) splits read operations from write operations. Each operation has a single, well-defined responsibility, which:

* **clarifies intent**: a `CreateUserCommand` does one thing, and its name says so;
* **keeps handlers small**: one message, one handler, easy to test in isolation;
* **makes side effects explicit**: events fan out to subscribers without coupling the producer to them.

CQRS is often discussed alongside distributed systems and Event Sourcing, but the pattern is just as useful in a local or monolithic application. The boundaries it draws are valuable on their own.

## Three message types

| Type      | Intent                             | Handlers           | Returns                    |
|-----------|------------------------------------|--------------------|----------------------------|
| `Command` | Change the state of the system     | Exactly one        | The handler's return value |
| `Query`   | Read state without side effects    | Exactly one        | The handler's return value |
| `Event`   | Notify that something has happened | Zero, one, or many | Nothing                    |

A `Command` is allowed to return a value (for convenience, typically an id or a result object), but that does not make it a query. Keep intent clear.

## Installation

Requires Python 3.12 or higher.

With the default DI backend ([python-injection](https://github.com/100nm/python-injection), recommended):

```bash
pip install "python-cq[injection]"
```

Without dependency injection (you will need to implement a `DIAdapter` to inject anything into your handlers):

```bash
pip install python-cq
```

## Quickstart

```python
import asyncio
from cq import CommandBus, command_handler
from dataclasses import dataclass
from injection import inject


@dataclass
class CreateUserCommand:
    name: str
    email: str


@command_handler
class CreateUserHandler:
    async def handle(self, command: CreateUserCommand) -> int:
        # ... persist the user, return its id
        return 42


@inject
async def main(bus: CommandBus[int]) -> None:
    command = CreateUserCommand(name="Ada", email="ada@example.com")
    user_id = await bus.dispatch(command)
    print(f"Created user {user_id}")


asyncio.run(main())
```

The decorator registers the handler against the type annotation of the first `handle` parameter. The bus is resolved by the DI container and forwards the command to that handler.

## Prerequisites

Familiarity with the following helps you get the most out of python-cq:

* **CQRS**, in particular the distinction between Commands, Queries, and Events.
* **Domain Driven Design (DDD)**, particularly aggregates and bounded contexts, which complement CQRS well.
