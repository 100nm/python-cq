# Defining messages and handlers

This guide covers how to define messages and their handlers for the three message types: `Command`, `Query`, and `Event`.

## Messages

A message is any Python object. Since messages are pure data containers, `dataclass` is a natural choice, but a `pydantic.BaseModel`, a `msgspec.Struct`, or any other class works just as well:

```python
from dataclasses import dataclass


@dataclass
class CreateUserCommand:
    name: str
    email: str
```

There is no base class to inherit from. The bus identifies a handler by inspecting the type annotation of the handler's `handle` method, not by a marker class.

## Handlers

A handler is a class with an async `handle` method that takes the message as its first parameter. Handlers are registered with one of the three decorators: `@command_handler`, `@query_handler`, or `@event_handler`.

```python
from cq import command_handler


@command_handler
class CreateUserHandler:
    async def handle(self, command: CreateUserCommand): ...
```

The decorator inspects the annotation on the first parameter of `handle` to determine which message type the handler subscribes to. All constructor dependencies are resolved at runtime by the configured DI adapter.

A command or a query accepts a single handler: registering a second one for the same message type raises a `RuntimeError` as soon as the module is imported. An event accepts any number of handlers.

### Using `NamedTuple` for handlers

Defining a handler as a `NamedTuple` gives you a concise, immutable declaration of its dependencies:

```python
from cq import command_handler
from typing import NamedTuple


@command_handler
class CreateUserHandler(NamedTuple):
    repository: UserRepository

    async def handle(self, command: CreateUserCommand): ...
```

`UserRepository` will be resolved by the DI container when the handler is instantiated.

### Polymorphic dispatch

A handler registered for a base class (or a `Protocol`, or a generic alias) will also receive any subclass of that type. This lets you write a single handler for a family of related messages:

```python
class DomainEvent: ...


class UserCreatedEvent(DomainEvent):
    user_id: int


@event_handler
class AuditLogger:
    async def handle(self, event: DomainEvent):
        # Receives UserCreatedEvent and any other DomainEvent subclass.
        ...
```

This applies to all three message types. Resolution uses the message's MRO and supports `type` aliases.

## Command handlers

Command handlers process commands and may return a value, typically an identifier or a small result object.

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

### Dispatching related events

A command handler can inject a `RelatedEvents` object to publish events as part of the command's execution:

```python
from cq import RelatedEvents, command_handler


@command_handler
class CreateUserHandler(NamedTuple):
    repository: UserRepository
    events: RelatedEvents

    async def handle(self, command: CreateUserCommand):
        ...
        self.events.add(UserCreatedEvent(user_id=user.id))
```

Calling `events.add(...)` schedules each event on a task group that lives for the duration of the command dispatch scope. Events are dispatched concurrently, and the command dispatch only returns once every scheduled event has been fully handled.

If an event handler raises, the exception propagates back to the caller of the command, wrapped in two nested `ExceptionGroup`s: one for the events scheduled by the command, one for the handlers of that event. Catch it with `except*`, which matches through any level of nesting.

You can add multiple events in one call:

```python
self.events.add(event_1, event_2)
```

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

Event handlers react to events that have already happened in the system. Unlike commands and queries, an event can have zero, one, or many handlers, which makes events the right tool for loose coupling between components.

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

Both handlers above receive the same event, and they run concurrently when the event is dispatched.

### `fail_silently`

By default, an exception raised inside an event handler propagates to the caller of `EventBus.dispatch`. For non-critical handlers (telemetry, audit logging, best-effort notifications) you can suppress that propagation:

```python
@event_handler(fail_silently=True)
class TrackUserCreatedHandler(NamedTuple):
    analytics: AnalyticsService

    async def handle(self, event: UserCreatedEvent):
        # An exception here will be swallowed after middlewares run.
        ...
```

Middlewares still see the exception before it is suppressed, so you can log it or record metrics in a middleware while the rest of the system carries on.

`fail_silently` is also accepted on `@command_handler` and `@query_handler`. In that case, when the handler raises, `dispatch` returns the `NotImplemented` sentinel instead of propagating the exception.
