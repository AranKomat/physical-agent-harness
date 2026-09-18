from __future__ import annotations

from collections import deque
from collections.abc import Callable

from .contracts import RuntimeEvent


class EventBus:
    """Small synchronous event bus for the first experiment.

    Replace with an async/distributed transport only after the synchronous
    control path is proven. Keeping this simple makes event ordering explicit.
    """

    def __init__(self, history: int = 256):
        self._subs: list[Callable[[RuntimeEvent], None]] = []
        self._history: deque[RuntimeEvent] = deque(maxlen=history)

    def subscribe(self, fn: Callable[[RuntimeEvent], None]) -> None:
        self._subs.append(fn)

    def publish(self, event: RuntimeEvent) -> None:
        self._history.append(event)
        for fn in tuple(self._subs):
            fn(event)

    def recent(self, n: int = 20) -> list[RuntimeEvent]:
        if n < 0:
            raise ValueError("n must be nonnegative")
        return list(self._history)[-n:] if n else []
