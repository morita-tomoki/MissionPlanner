"""Shared I/O contracts between a Vehicle and its protocols.

A Vehicle provides these primitives; protocols consume them. Defined here (a
lower layer than `vehicle`) so both sides can depend on it without an import
cycle — the Vehicle imports these types and implements them.

- ``request``: send a message and await the single matching reply (one-shot).
- ``open_stream``: send nothing; receive every matching message until closed —
  used for streamed responses like a full parameter download.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from missionctl.core.codec import MavlinkMessage

Predicate = Callable[[MavlinkMessage], bool]
MakeFn = Callable[..., MavlinkMessage]
SendFn = Callable[[MavlinkMessage], Awaitable[None]]
RequestFn = Callable[[MavlinkMessage, Predicate, float], Awaitable[MavlinkMessage]]


class MessageStream:
    """A live feed of incoming messages matching a predicate. Close when done
    (or use as a context manager) to unregister it from the vehicle."""

    def __init__(self, queue: asyncio.Queue[MavlinkMessage], close: Callable[[], None]) -> None:
        self._queue = queue
        self._close = close

    async def next(self, timeout: float) -> MavlinkMessage:
        """Await the next matching message, or raise ``TimeoutError``."""
        async with asyncio.timeout(timeout):
            return await self._queue.get()

    def close(self) -> None:
        self._close()

    def __enter__(self) -> MessageStream:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


OpenStreamFn = Callable[[Predicate], MessageStream]
