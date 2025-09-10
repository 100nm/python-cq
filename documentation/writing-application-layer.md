# Writing Application Layer

Set of tools to simplify application logic writing.

* [Reading](#reading)
* [Writing](#writing)
* [Side effects](#side-effects)
* [Bus Middleware](#bus-middleware)

## Reading

### Define a query

The purpose of a query is to read data.

The `query_handler` decorator associates a query type with a particular logic (handler).
Only one handler can be associated with a query type.
All handler dependencies are injected at runtime using [python-injection](https://github.com/100nm/python-injection).

```python
import msgspec
from cq import query_handler

class UserProfileView:
    """ Data to retrieve """

class ReadUserProfileQuery(msgspec.Struct, frozen=True):
    user_id: int

@query_handler
class ReadUserProfileHandler:
    async def handle(self, query: ReadUserProfileQuery) -> UserProfileView:
        """ User profile reading logic """
```

### Execute a query

To execute a query, it must be transmitted to the `QueryBus`.
To retrieve a bus instance, use [python-injection](https://github.com/100nm/python-injection).

The generic parameter of the `QueryBus` is the expected type when the dispatch method returns.

```python
from cq import QueryBus
from injection import inject

@inject
async def get_user_profile_1(query_bus: QueryBus[UserProfileView]) -> UserProfileView:
    query = ReadUserProfileQuery(user_id=1)
    user_profile = await query_bus.dispatch(query)
    return user_profile
```

## Writing

### Define a command

The purpose of a command is to write data.

The `command_handler` decorator associates a command type with a particular logic (handler).
Only one handler can be associated with a command type.
All handler dependencies are injected at runtime using [python-injection](https://github.com/100nm/python-injection).

```python
from cq import command_handler

class UpdateUserProfileCommand:
    """ Data required to update user profile """

@command_handler
class UpdateUserProfileHandler:
    async def handle(self, command: UpdateUserProfileCommand) -> None:
        """ User profile updating logic """
```

### Execute a command

To execute a command, it must be transmitted to the `CommandBus`.
To retrieve a bus instance, use [python-injection](https://github.com/100nm/python-injection).

The generic parameter of the `CommandBus` is the expected type when the dispatch method returns.

```python
from cq import CommandBus
from injection import inject

@inject
async def update_user_profile(command_bus: CommandBus[None]) -> None:
    command = UpdateUserProfileCommand(...)
    await command_bus.dispatch(command)
```

## Side effects

### Define an event

The purpose of an event is to execute side effects.
An event is generally propagated at the end of a command.

The `event_handler` decorator associates a event type with a particular logic (handler).
Several handlers can be associated with an event type.
All handler dependencies are injected at runtime using [python-injection](https://github.com/100nm/python-injection).

```python
from cq import event_handler

class UserRegistered:
    """ Data to process the event """

@event_handler
class SendConfirmationEmailHandler:
    async def handle(self, event: UserRegistered) -> None:
        """ Confirmation email sending logic """
```

### Propagate an event

To propagate an event, it must be transmitted to `RelatedEvents` instance.

```python
from cq import RelatedEvents, command_handler

class UserRegistrationCommand:
    """ Data required to register a user """

@command_handler
class UserRegistrationHandler:
    def __init__(self, related_events: RelatedEvents) -> None:
        self.related_events = related_events

    async def handle(self, command: UserRegistrationCommand) -> None:
        # User registration logic
        # ...
        event = UserRegistered(...)
        self.related_events.add(event)
```

## Bus Middleware

### Define a middleware

Acts as classic middleware. It is used around the call of a handler.

> [!NOTE]
> * It isn't possible to replace the result returned by the handler.
> * If an exception is caught but no other exception is raised, `Bus.dispatch` will return `NotImplemented`.

As a function:

```python
from cq import MiddlewareResult

InputType = ...
OutputType = ...

async def some_middleware(input_value: InputType) -> MiddlewareResult[OutputType]:
    # do something before the handler is executed
    output_value = yield
    # do something after the handler is executed
```

As a class:

```python
from cq import MiddlewareResult

class SomeMiddleware:
    async def __call__(self, input_value: InputType) -> MiddlewareResult[OutputType]:
        # do something before the handler is executed
        output_value = yield
        # do something after the handler is executed
```

### Add middleware

To add a middleware, you need to override the bus recipe.

```python
from cq import CommandBus, new_command_bus
from injection import injectable

@injectable
def override_command_bus_recipe() -> CommandBus:
    bus = new_command_bus()
    bus.add_middlewares(log_middleware, transaction_middleware)
    return bus
```
