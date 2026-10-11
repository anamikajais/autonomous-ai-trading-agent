import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Type

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._subscribers: Dict[Type, List[Callable[[Any], Awaitable[None]]]] = {}

    def subscribe(self, event_type: Type, handler: Callable[[Any], Awaitable[None]]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed {handler.__name__} to {event_type.__name__}")

    async def publish(self, event: Any):
        event_type = type(event)
        if event_type in self._subscribers:
            handlers = self._subscribers[event_type]
            await asyncio.gather(*(handler(event) for handler in handlers))
