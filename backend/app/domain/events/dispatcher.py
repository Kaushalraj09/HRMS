from typing import Callable, Dict, List, Type
import logging

logger = logging.getLogger(__name__)

class DomainEvent:
    """Base class for all domain events."""
    pass

# Type alias for event listeners
EventListener = Callable[[DomainEvent], None]

class EventDispatcher:
    _listeners: Dict[Type[DomainEvent], List[EventListener]] = {}

    @classmethod
    def register(cls, event_type: Type[DomainEvent], listener: EventListener) -> None:
        """Register a subscriber/listener for a specific domain event type."""
        if event_type not in cls._listeners:
            cls._listeners[event_type] = []
        cls._listeners[event_type].append(listener)
        logger.info(f"Registered listener {listener.__name__ if hasattr(listener, '__name__') else listener} for event {event_type.__name__}")

    @classmethod
    def clear(cls) -> None:
        """Clear all registered event listeners."""
        cls._listeners.clear()

    @classmethod
    def dispatch(cls, event: DomainEvent) -> None:
        """Dispatch a domain event to all registered listeners."""
        event_type = type(event)
        listeners = cls._listeners.get(event_type, [])
        logger.info(f"Dispatching event {event_type.__name__} to {len(listeners)} listeners.")
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error executing listener {listener.__name__ if hasattr(listener, '__name__') else listener} for event {event_type.__name__}: {e}", exc_info=True)
