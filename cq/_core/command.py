from abc import ABC
from typing import Any

import injection

from cq._core.bus import Bus, SimpleBus, SubscriberDecorator
from cq._core.dto import DTO


class Command(DTO, ABC):
    __slots__ = ()


type CommandBus[T] = Bus[Command, T]
command_handler: SubscriberDecorator[Command, Any] = SubscriberDecorator(CommandBus)

injection.set_constant(SimpleBus(), CommandBus, alias=True)


def find_command_bus[T]() -> CommandBus[T]:
    return injection.find_instance(CommandBus)
