"""Async UDP transport.

This is the transport used to reach ArduPilot SITL (default ``udp:127.0.0.1:14550``):

    listener = UdpLink(local_addr=("0.0.0.0", 14550))   # GCS listens; learns peer
    sender   = UdpLink(remote_addr=("127.0.0.1", 14550)) # connected socket

A listen-mode link learns its peer from the first datagram and replies there; a
remote-mode link uses a connected socket. No polling — datagrams arrive via the
asyncio event loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import cast

from missionctl.core.link.base import Link, LinkState
from missionctl.core.util.observable import Observable


class _DatagramProtocol(asyncio.DatagramProtocol):
    def __init__(
        self,
        on_datagram: Callable[[bytes, object], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        self._on_datagram = on_datagram
        self._on_error = on_error

    def datagram_received(self, data: bytes, addr: object) -> None:
        self._on_datagram(data, addr)

    def error_received(self, exc: Exception) -> None:
        self._on_error(exc)


class UdpLink(Link):
    def __init__(
        self,
        *,
        local_addr: tuple[str, int] | None = None,
        remote_addr: tuple[str, int] | None = None,
    ) -> None:
        if local_addr is None and remote_addr is None:
            raise ValueError("UdpLink needs local_addr (listen) or remote_addr (send)")
        self._local = local_addr
        self._remote = remote_addr
        self._peer: object | None = remote_addr
        self._state: Observable[LinkState] = Observable(LinkState.DISCONNECTED)
        self._inbound: asyncio.Queue[bytes] = asyncio.Queue()
        self._transport: asyncio.DatagramTransport | None = None

    @property
    def state(self) -> Observable[LinkState]:
        return self._state

    @property
    def local_port(self) -> int:
        if self._transport is None:
            raise RuntimeError("link not open")
        sockname = self._transport.get_extra_info("sockname")
        return cast("tuple[str, int]", sockname)[1]

    async def open(self) -> None:
        self._state.set(LinkState.CONNECTING)
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _DatagramProtocol(self._handle_datagram, self._handle_error),
            local_addr=self._local,
            remote_addr=self._remote,
        )
        self._transport = transport
        self._state.set(LinkState.CONNECTED)

    async def read(self) -> bytes:
        return await self._inbound.get()

    async def write(self, data: bytes) -> None:
        if self._transport is None:
            raise RuntimeError("link not open")
        if self._remote is not None:
            # Connected socket — no explicit address.
            self._transport.sendto(data)
        elif self._peer is not None:
            self._transport.sendto(data, cast("tuple[str, int]", self._peer))
        else:
            raise RuntimeError("no UDP peer known yet (nothing received to reply to)")

    async def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._state.set(LinkState.DISCONNECTED)

    def _handle_datagram(self, data: bytes, addr: object) -> None:
        self._peer = addr
        self._inbound.put_nowait(data)

    def _handle_error(self, _exc: Exception) -> None:
        self._state.set(LinkState.ERROR)
