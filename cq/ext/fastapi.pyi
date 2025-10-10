from cq import Command, DeferredBus, Event, Query

type DeferredCommandBus = DeferredBus[Command]
type DeferredEventBus = DeferredBus[Event]
type DeferredQueryBus = DeferredBus[Query]
