"""Event system for simulation observability."""

from collections import defaultdict
from typing import Any, Callable


EventCallback = Callable[..., None]

# Event types:
# CELL_BORN     — cell, parent
# CELL_DIED     — cell, cause (reaper/lazy/disturbance)
# NEW_GENOTYPE  — genotype
# GENOTYPE_EXTINCT — genotype
# MUTATION      — addr, kind (background/copy/division)
# MILESTONE     — inst_executed


class EventBus:
    """Simple synchronous observer pattern for simulation events."""

    def __init__(self):
        self._subscribers: dict[str, list[EventCallback]] = defaultdict(list)
        self._enabled: bool = True

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        """Register a callback for an event type."""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
        """Remove a callback."""
        try:
            self._subscribers[event_type].remove(callback)
        except ValueError:
            pass

    def emit(self, event_type: str, **kwargs: Any) -> None:
        """Fire an event, calling all registered callbacks."""
        if not self._enabled:
            return
        for cb in self._subscribers.get(event_type, []):
            cb(**kwargs)

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def clear(self) -> None:
        """Remove all subscribers."""
        self._subscribers.clear()

    @property
    def enabled(self) -> bool:
        return self._enabled
