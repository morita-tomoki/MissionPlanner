"""MAVLink codec — pymavlink used strictly for framing (see ADR-0004). No I/O.

pymavlink owns no socket or serial handle in this project; it only turns bytes
into messages and back. Transport lives in ``missionctl.core.link``.

pymavlink ships no type stubs, so this one module runs under a relaxed pyright
execution environment (see ``pyproject.toml``). The *public* surface stays fully
typed via the ``MavlinkMessage`` protocol, so the rest of the strict core sees a
clean, typed boundary. Callers should not import pymavlink directly — build
dialect messages through :attr:`MavlinkCodec.raw`.
"""

from __future__ import annotations

from typing import Any, Protocol, cast

from pymavlink.dialects.v20 import ardupilotmega as mavlink


class MavlinkMessage(Protocol):
    """The minimal, typed surface of a decoded MAVLink message that core uses."""

    def get_type(self) -> str: ...
    def get_srcSystem(self) -> int: ...
    def get_srcComponent(self) -> int: ...
    def to_dict(self) -> dict[str, Any]: ...


class MavlinkCodec:
    """Stateful byte <-> message codec.

    Use one instance per link: the parser keeps internal state so a MAVLink frame
    split across multiple ``read()`` chunks is reassembled correctly.
    """

    def __init__(self, *, system_id: int = 255, component_id: int = 0) -> None:
        self._mav = mavlink.MAVLink(None, srcSystem=system_id, srcComponent=component_id)
        # Never raise on a corrupt/partial byte run — just skip and resync.
        self._mav.robust_parsing = True

    def decode(self, data: bytes) -> list[MavlinkMessage]:
        """Feed received bytes; return zero or more fully-parsed messages.

        With robust parsing, pymavlink yields a ``MAVLink_bad_data`` sentinel for
        unparseable byte runs instead of raising. We drop those here so callers see
        only real messages. (Link-quality accounting can consume them separately
        later.)
        """
        messages = self._mav.parse_buffer(data) or []
        real = [m for m in messages if m.get_type() != "BAD_DATA"]
        return cast("list[MavlinkMessage]", real)

    def encode(self, message: Any) -> bytes:
        """Serialize a dialect message (built via :attr:`raw` or :meth:`make`)."""
        return cast(bytes, message.pack(self._mav))

    def make(self, msg_type: str, **fields: Any) -> MavlinkMessage:
        """Construct an outbound dialect message by snake_case name, e.g.
        ``make("command_long", target_system=1, ...)``. Keeps pymavlink message
        construction confined to this module (callers build commands through here)."""
        cls = getattr(mavlink, f"MAVLink_{msg_type}_message")
        return cast("MavlinkMessage", cls(**fields))

    @property
    def raw(self) -> Any:
        """Escape hatch to construct dialect messages/constants (e.g. commands),
        keeping the pymavlink import confined to this module. Use sparingly."""
        return mavlink
