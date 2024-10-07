# Writing Application Layer

Set of tools to simplify application logic writing.

* [Data Transfer Object (DTO)](#data-transfer-object-dto)
* [Reading](#reading)
* [Writing](#writing)
* [Side effects](#side-effects)
* [Bus Middleware](#bus-middleware)

## Data Transfer Object (DTO)

The idea is to have one DTO to enter the application layer and another to exit when needed.
A DTO is a subclass of [Pydantic BaseModel](https://docs.pydantic.dev/latest/), so it contains all these properties.

```python
from cq import DTO

class MyAwesomeDTO(DTO):
    my_awesome_value: str
```

## Reading

### Define a query

The purpose of a query is to read data.
The `Query` class is a subclass of DTO.

The `query_handler` decorator associates a query type with a particular logic (handler).
Only one handler can be associated with a query type.
All handler dependencies are injected at runtime using [python-injection](https://github.com/100nm/python-injection).

```python
from cq import DTO, Query, query_handler

class UserProfileView(DTO):
    """ Data to retrieve """

class ReadUserProfileQuery(Query):
    user_id: int

@query_handler(ReadUserProfileQuery)
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
The `Command` class is a subclass of DTO.

The `command_handler` decorator associates a command type with a particular logic (handler).
Only one handler can be associated with a command type.
All handler dependencies are injected at runtime using [python-injection](https://github.com/100nm/python-injection).

```python
from cq import Command, command_handler

class UpdateUserProfileCommand(Command):
    """ Data required to update user profile """

@command_handler(UpdateUserProfileCommand)
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
The `Event` class is a subclass of DTO.

The `event_handler` decorator associates a event type with a particular logic (handler).
Several handlers can be associated with an event type.
All handler dependencies are injected at runtime using [python-injection](https://github.com/100nm/python-injection).

```python
from cq import Event, event_handler

class UserRegistered(Event):
    """ Data to process the event """

@event_handler(UserRegistered)
class SendConfirmationEmailHandler:
    async def handle(self, event: UserRegistered) -> None:
        """ Confirmation email sending logic """
```

### Propagate an event

To propagate an event, it must be transmitted to the `EventBus`.
To retrieve a bus instance, use [python-injection](https://github.com/100nm/python-injection).

```python
from cq import Command, EventBus, command_handler

class UserRegistrationCommand(Command):
    """ Data required to register a user """

@command_handler(UserRegistrationCommand)
class UserRegistrationHandler:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def handle(self, command: UserRegistrationCommand) -> None:
        # User registration logic
        # ...
        event = UserRegistered(...)
        self.event_bus.dispatch_no_wait(event)
```

## Bus Middleware

### Define a middleware

Acts as classic middleware. It is used around the call of a handler.

> **Note**
> 
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

To add a middleware :

1. Retrieve a bus instance of your choice.
2. Use the `add_middlewares` method.

```python
from cq import CommandBus
from typing import Any
from injection import inject

@inject
def setup_command_bus(command_bus: CommandBus[Any]) -> None:
    command_bus.add_middlewares(log_middleware, transaction_middleware)
```
