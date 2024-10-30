from abc import ABC
from typing import Any

import injection

from cq._core.dispatcher.bus import Bus, SimpleBus, SubscriberDecorator
from cq._core.dto import DTO


class Command(DTO, ABC):
    __slots__ = ()


type CommandBus[T] = Bus[Command, T]
AnyCommandBus = CommandBus[Any]
command_handler: SubscriberDecorator[Command, Any] = SubscriberDecorator(CommandBus)

injection.set_constant(SimpleBus(), CommandBus, alias=True)


def find_command_bus[T]() -> CommandBus[T]:
    return injection.find_instance(CommandBus)
