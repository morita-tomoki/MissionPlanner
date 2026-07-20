"""In-memory Link for tests: inject inbound bytes with ``feed()`` and inspect
outbound bytes via ``sent``. No sockets, fully deterministic.
"""

from __future__ import annotations

import asyncio

from missionctl.core.link.base import Link, LinkState
from missionctl.core.util.observable import Observable


class LoopbackLink(Link):
    def __init__(self) -> None:
        self._state: Observable[LinkState] = Observable(LinkState.DISCONNECTED)
        self._inbound: asyncio.Queue[bytes] = asyncio.Queue()
        self.sent: list[bytes] = []

    @property
    def state(self) -> Observable[LinkState]:
        return self._state

    async def open(self) -> None:
        self._state.set(LinkState.CONNECTED)

    async def read(self) -> bytes:
        return await self._inbound.get()

    async def write(self, data: bytes) -> None:
        self.sent.append(data)

    async def close(self) -> None:
        self._state.set(LinkState.DISCONNECTED)

    def feed(self, data: bytes) -> None:
        """Make ``data`` available to the next ``read()`` (test-side injection)."""
        self._inbound.put_nowait(data)
