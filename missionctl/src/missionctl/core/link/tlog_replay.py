"""Replays a MissionPlanner / MAVProxy ``.tlog``.

A tlog is a sequence of records: an 8-byte big-endian microsecond timestamp
followed by one raw MAVLink frame. This link strips the timestamp and yields one
frame per ``read()``, returning ``b""`` at end of file. It is the backbone of
deterministic regression tests — feed a recorded flight through the same codec
path used in production. (Timestamp-paced replay can be layered on later.)
"""

from __future__ import annotations

from pathlib import Path

from missionctl.core.link.base import Link, LinkState
from missionctl.core.util.observable import Observable

_TIMESTAMP_BYTES = 8


def _frame_length(buf: bytes, pos: int) -> int | None:
    """Total length of the MAVLink frame starting at ``buf[pos]``, or None if the
    buffer is too short to tell."""
    if pos >= len(buf):
        return None
    magic = buf[pos]
    if magic == 0xFE:  # v1: STX,LEN,SEQ,SYS,COMP,MSGID(1),payload,CRC(2)
        if pos + 1 >= len(buf):
            return None
        payload = buf[pos + 1]
        return 6 + payload + 2
    if magic == 0xFD:  # v2: STX,LEN,incompat,compat,SEQ,SYS,COMP,MSGID(3),payload,CRC(2)[,SIG(13)]
        if pos + 2 >= len(buf):
            return None
        payload = buf[pos + 1]
        incompat = buf[pos + 2]
        signature = 13 if (incompat & 0x01) else 0
        return 10 + payload + 2 + signature
    return None


class TlogReplayLink(Link):
    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._buf = b""
        self._pos = 0
        self._state: Observable[LinkState] = Observable(LinkState.DISCONNECTED)

    @property
    def state(self) -> Observable[LinkState]:
        return self._state

    async def open(self) -> None:
        self._buf = self._path.read_bytes()
        self._pos = 0
        self._state.set(LinkState.CONNECTED)

    async def read(self) -> bytes:
        frame = self._next_frame()
        if frame is None:
            self._state.set(LinkState.DISCONNECTED)
            return b""
        return frame

    async def write(self, data: bytes) -> None:
        raise RuntimeError("TlogReplayLink is read-only")

    async def close(self) -> None:
        self._state.set(LinkState.DISCONNECTED)

    def _next_frame(self) -> bytes | None:
        if self._pos + _TIMESTAMP_BYTES > len(self._buf):
            return None
        start = self._pos + _TIMESTAMP_BYTES
        length = _frame_length(self._buf, start)
        if length is None:
            return None
        end = start + length
        if end > len(self._buf):
            return None
        self._pos = end
        return self._buf[start:end]
