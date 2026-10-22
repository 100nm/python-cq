# Messages and handlers

This guide covers how to define messages and how to register the handlers that process them, for the three message types: `Command`, `Query`, and `Event`.

## Messages

A message is any Python object. Messages are pure data, so `dataclass` is a natural choice, but a `pydantic.BaseModel`, a `msgspec.Struct`, or any other class works just as well:

```python
from dataclasses import dataclass


@dataclass
class CreateUserCommand:
    name: str
    email: str
```

There is no base class to inherit from. `Command`, `Query`, and `Event` exported by `cq` are aliases of `object`, used only to make type hints read better. A handler is matched to a message by the type annotation of its `handle` method, not by a marker class.

## Handlers

A handler is a class with an async `handle` method that takes the message as its first parameter. It is registered with one of the three decorators: `@command_handler`, `@query_handler`, or `@event_handler`.

```python
from cq import command_handler


@command_handler
class CreateUserHandler:
    async def handle(self, command: CreateUserCommand) -> int: ...
```

The decorator reads the annotation of the first parameter of `handle` to know which message type the handler subscribes to. A missing annotation raises a `TypeError` at import time.

A new handler instance is built for every dispatch, through the configured DI adapter, so constructor dependencies are injected each time the handler runs.

A command or a query accepts a single handler: registering a second one for the same message type raises a `RuntimeError` as soon as the module is imported. An event accepts any number of handlers.

### Declaring dependencies

Defining a handler as a `NamedTuple` (or a frozen `dataclass`) gives a concise, immutable declaration of its dependencies:

```python
from cq import command_handler
from typing import NamedTuple


@command_handler
class CreateUserHandler(NamedTuple):
    repository: UserRepository

    async def handle(self, command: CreateUserCommand) -> int:
        user = await self.repository.create(command.name, command.email)
        return user.id
```

`UserRepository` is resolved by the DI container when the handler is instantiated.

### Explicit message type

The message type can be passed to the decorator instead of being read from the annotation. It takes precedence over the annotation:

```python
@command_handler(CreateUserCommand)
class CreateUserHandler:
    async def handle(self, command) -> int: ...
```

### Polymorphic dispatch

A handler registered for a base class also receives every subclass of that type. This lets you write a single handler for a family of related messages:

```python
from cq import event_handler
from dataclasses import dataclass


class DomainEvent: ...


@dataclass
class UserCreatedEvent(DomainEvent):
    user_id: int


@event_handler
class AuditLogger:
    async def handle(self, event: DomainEvent):
        # Receives UserCreatedEvent and any other DomainEvent subclass.
        ...
```

Resolution walks the message's MRO and also understands generic aliases and `type` aliases. A union annotation registers the handler once per member, so `event: UserCreatedEvent | UserDeletedEvent` subscribes to both types.

When several handlers match through the MRO, a command or a query goes to the most specific one: a handler registered for a subclass wins over one registered for its base class. An event goes to all of them.

## Command handlers

Command handlers change the state of the system and may return a value, typically an identifier or a small result object.

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

    async def handle(self, command: CreateUserCommand) -> int:
        user = await self.repository.create(command.name, command.email)
        return user.id
```

### Related events

A command handler can inject `RelatedEvents` to publish events as part of the command's execution:

```python
from cq import RelatedEvents, command_handler


@command_handler
class CreateUserHandler(NamedTuple):
    repository: UserRepository
    events: RelatedEvents

    async def handle(self, command: CreateUserCommand) -> int:
        user = await self.repository.create(command.name, command.email)
        self.events.add(UserCreatedEvent(user_id=user.id))
        return user.id
```

`events.add(...)` accepts any number of events and schedules each one on a task group that lives for the duration of the command dispatch. Events start as soon as the handler gives control back to the event loop (at its next `await`, or when it returns) and run concurrently with the rest of the handler. The command dispatch only returns once every scheduled event has been fully handled. Where you call `add` therefore says something: as the last line, nothing after it depends on the event; in the middle of the handler, the remaining work runs concurrently with the event handlers.

Scheduled events are handled even if the command handler raises afterwards: nothing is rolled back. Call `add` once the work the event reports has actually succeeded. For the same reason, a command retried by `RetryMiddleware` publishes the events of every failed attempt.

If an event handler raises, the command handler is cancelled if it is still running, and the exception propagates back to the caller of the command, wrapped in two nested `ExceptionGroup`s: one for the events scheduled by the command, one for the handlers of that event. Catch it with `except*`, which matches through any level of nesting.

`RelatedEvents` is provided by the command scope of the DI adapter. With the `[injection]` extra it works out of the box; with a custom adapter, see [Custom DI adapter](di.md).

## Query handlers

Query handlers read state and must not produce side effects.

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
        return await self.repository.get(query.user_id)
```

## Event handlers

Event handlers react to something that has already happened. An event can have zero, one, or many handlers, which makes events the right tool for loose coupling between components.

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
        await self.email_service.send_welcome(event.user_id)


@event_handler
class TrackUserCreatedHandler(NamedTuple):
    analytics: AnalyticsService

    async def handle(self, event: UserCreatedEvent):
        await self.analytics.track("user_created", event.user_id)
```

Both handlers receive the same event and run concurrently when it is dispatched.

## `fail_silently`

By default, an exception raised inside a handler propagates to the caller of `dispatch`. For non-critical handlers (telemetry, audit logging, best-effort notifications) you can suppress it:

```python
@event_handler(fail_silently=True)
class TrackUserCreatedHandler(NamedTuple):
    analytics: AnalyticsService

    async def handle(self, event: UserCreatedEvent):
        # An exception here is swallowed once the middlewares have seen it.
        ...
```

Middlewares still see the exception before it is suppressed, so a middleware can log it or record metrics while the rest of the system carries on.

`fail_silently` is accepted by the three decorators. On a command or a query handler, `dispatch` returns the `NotImplemented` sentinel instead of raising.
