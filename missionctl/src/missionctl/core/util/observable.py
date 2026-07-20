"""A tiny synchronous observable used to publish immutable state snapshots.

Subscriptions are tracked by a monotonic integer token and disposed via an explicit
handle. This deliberately avoids identifying subscriptions by object hash — the
legacy MissionPlanner used ``GetHashCode()`` as the subscription id, so two
identical subscriptions collided and an unsubscribe could remove the wrong one.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class Subscription:
    """Handle returned by :meth:`Observable.subscribe`. Dispose to stop delivery.

    Usable as a context manager: ``with obs.subscribe(cb): ...``.
    """

    def __init__(self, unsubscribe: Callable[[], None]) -> None:
        self._unsubscribe = unsubscribe
        self._active = True

    def dispose(self) -> None:
        if self._active:
            self._active = False
            self._unsubscribe()

    def __enter__(self) -> Subscription:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.dispose()


class Observable(Generic[T]):
    """Holds a current value and notifies observers on change."""

    def __init__(self, initial: T) -> None:
        self._value = initial
        self._observers: dict[int, Callable[[T], None]] = {}
        self._next_id = 0

    @property
    def value(self) -> T:
        return self._value

    def set(self, value: T) -> None:
        self._value = value
        # Snapshot the observers so a handler may (un)subscribe during delivery.
        for observer in list(self._observers.values()):
            observer(value)

    def subscribe(
        self, observer: Callable[[T], None], *, emit_current: bool = True
    ) -> Subscription:
        token = self._next_id
        self._next_id += 1
        self._observers[token] = observer

        def _unsubscribe() -> None:
            self._observers.pop(token, None)

        if emit_current:
            observer(self._value)
        return Subscription(_unsubscribe)
