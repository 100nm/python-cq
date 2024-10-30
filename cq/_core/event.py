from abc import ABC

import injection

from cq._core.dispatcher.bus import Bus, SubscriberDecorator, TaskBus
from cq._core.dto import DTO


class Event(DTO, ABC):
    __slots__ = ()


type EventBus = Bus[Event, None]
event_handler: SubscriberDecorator[Event, None] = SubscriberDecorator(EventBus)

injection.set_constant(TaskBus(), EventBus, alias=True)


def find_event_bus() -> EventBus:
    return injection.find_instance(EventBus)
