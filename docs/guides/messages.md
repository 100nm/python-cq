# Defining messages and handlers

This guide explains how to define messages and their handlers for the three message types: Command, Query, and Event.

## Messages

A message can be any Python object. Since messages are simple data containers, using a `dataclass` is a natural choice:

```python
from dataclasses import dataclass

@dataclass
class CreateUserCommand:
    name: str
    email: str
```

## Handlers

A handler is a class with an async `handle` method that receives the message as its parameter. Handlers are registered using a decorator placed above the class definition: `@command_handler`, `@query_handler`, or `@event_handler`.

The decorator inspects the `handle` method signature to determine which message type it should process.

```python
from cq import command_handler

@command_handler
class CreateUserHandler:
    async def handle(self, command: CreateUserCommand):
        ...
```

All constructor dependencies are resolved at runtime by the configured DI adapter.

### Using NamedTuple for handlers

It is recommended to define handlers as `NamedTuple` for a more concise class definition and immutability:

```python
from cq import command_handler
from typing import NamedTuple

@command_handler
class CreateUserHandler(NamedTuple):
    repository: UserRepository

    async def handle(self, command: CreateUserCommand):
        ...
```

## Command handlers

Command handlers process commands and may return a value for convenience.

```python
from cq import command_handler
from dataclasses import dataclass
from typing import NamedTuple

@dataclass
class CreateUserCommand:
    name: str
    email: str

@command_handler
class CreateUserHandler(NamedTuple):
    repository: UserRepository

    async def handle(self, command: CreateUserCommand):
        ...
```

### Dispatching related events

Command handlers can inject a `RelatedEvents` object to automatically dispatch events after the command is processed:

```python
from cq import RelatedEvents, command_handler

@command_handler
class CreateUserHandler(NamedTuple):
    repository: UserRepository
    events: RelatedEvents

    async def handle(self, command: CreateUserCommand):
        ...
        event = UserCreatedEvent(...)
        self.events.add(event)
```

You can add multiple events at once:

```python
self.events.add(event_1, event_2)
```

## Query handlers

Query handlers process queries and return data without side effects.

```python
from cq import query_handler
from dataclasses import dataclass
from typing import NamedTuple

@dataclass
class GetUserByIdQuery:
    user_id: int

@query_handler
class GetUserByIdHandler(NamedTuple):
    repository: UserRepository

    async def handle(self, query: GetUserByIdQuery) -> User:
        ...
```

## Event handlers

Event handlers react to events that have occurred in the system. Unlike commands and queries, an event can be handled by multiple handlers, enabling loose coupling between components.

```python
from cq import event_handler
from dataclasses import dataclass
from typing import NamedTuple

@dataclass
class UserCreatedEvent:
    user_id: int

@event_handler
class SendWelcomeEmailHandler(NamedTuple):
    email_service: EmailService

    async def handle(self, event: UserCreatedEvent):
        ...

@event_handler
class TrackUserCreatedHandler(NamedTuple):
    analytics: AnalyticsService

    async def handle(self, event: UserCreatedEvent):
        ...
```

### fail_silently

The `fail_silently` option suppresses any exception raised by the handler instead of propagating it to the caller. Exceptions can still be caught and handled by middlewares before being suppressed.

This is particularly useful for non-critical event handlers where a failure should not affect the rest of the system:

```python
@event_handler(fail_silently=True)
class TrackUserCreatedHandler(NamedTuple):
    analytics: AnalyticsService

    async def handle(self, event: UserCreatedEvent):
        # An exception here won't propagate to the caller
        ...
```
