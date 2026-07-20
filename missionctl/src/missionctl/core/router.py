"""Demultiplexes decoded MAVLink messages to per-vehicle handlers by
``(sysid, compid)``.

The router holds handler callbacks, not ``Vehicle`` objects, so it has no
dependency on the vehicle/fleet layers (they wire themselves in). This replaces
the legacy global ``sysidcurrent`` — routing is explicit and per-message.
"""

from __future__ import annotations

from collections.abc import Callable

from missionctl.core.codec import MavlinkMessage

Address = tuple[int, int]
Handler = Callable[[MavlinkMessage], None]


class Router:
    def __init__(self) -> None:
        self._handlers: dict[Address, Handler] = {}
        self._on_unknown: Callable[[Address, MavlinkMessage], None] | None = None

    def register(self, address: Address, handler: Handler) -> None:
        self._handlers[address] = handler

    def unregister(self, address: Address) -> None:
        self._handlers.pop(address, None)

    def on_unknown(self, callback: Callable[[Address, MavlinkMessage], None]) -> None:
        """Called for a message whose (sysid, compid) has no handler — e.g. to
        auto-create a vehicle on first sighting."""
        self._on_unknown = callback

    def route(self, msg: MavlinkMessage) -> bool:
        """Deliver ``msg`` to its handler. Returns True if a handler existed."""
        address: Address = (msg.get_srcSystem(), msg.get_srcComponent())
        handler = self._handlers.get(address)
        if handler is not None:
            handler(msg)
            return True
        if self._on_unknown is not None:
            self._on_unknown(address, msg)
        return False
