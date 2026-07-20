"""Transport abstraction: an async, transport-agnostic byte stream.

Intentionally NOT shaped like a serial port. The legacy ``ICommsSerial`` forced
serial concepts (BaudRate, DTR, RTS, DataBits) onto TCP/UDP/BLE, which leaked
everywhere. Here, serial-only options live inside the serial implementation; the
abstraction is just: open, read bytes, write bytes, close, and observe state.
"""

from __future__ import annotations

import enum
from typing import Protocol

from missionctl.core.util.observable import Observable


class LinkState(enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class Link(Protocol):
    """An async byte-stream transport (serial / TCP / UDP / file replay / …).

    Implementations must never block a thread with polling sleeps; reads await
    real data (backpressure via the underlying asyncio transport).
    """

    @property
    def state(self) -> Observable[LinkState]:
        """Observable connection state."""
        ...

    async def open(self) -> None: ...

    async def read(self) -> bytes:
        """Return the next chunk of received bytes (may be partial frames)."""
        ...

    async def write(self, data: bytes) -> None: ...

    async def close(self) -> None: ...
