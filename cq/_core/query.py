from abc import ABC
from typing import Any

import injection

from cq._core.dispatcher.bus import Bus, SimpleBus, SubscriberDecorator
from cq._core.dto import DTO


class Query(DTO, ABC):
    __slots__ = ()


type QueryBus[T] = Bus[Query, T]
query_handler: SubscriberDecorator[Query, Any] = SubscriberDecorator(QueryBus)

injection.set_constant(SimpleBus(), QueryBus, alias=True)


def find_query_bus[T]() -> QueryBus[T]:
    return injection.find_instance(QueryBus)
