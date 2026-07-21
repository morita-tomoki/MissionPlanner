"""Mission protocol (MISSION_ITEM_INT variant) for ArduPlane.

- download: MISSION_REQUEST_LIST → MISSION_COUNT → N× (MISSION_REQUEST_INT →
  MISSION_ITEM_INT) → MISSION_ACK.
- upload: MISSION_COUNT → the vehicle drives it by asking for each item with
  MISSION_REQUEST_INT, which we answer with MISSION_ITEM_INT, until MISSION_ACK.
- set_current: MISSION_SET_CURRENT → MISSION_CURRENT.

Uses the Vehicle ``request`` primitive for one-shot exchanges and ``open_stream``
for the upload handshake (the vehicle sends a burst of item requests we must
answer). All async, with explicit timeouts; expected failures return a Result.
"""

from __future__ import annotations

from dataclasses import dataclass

from missionctl.core.codec import MavlinkMessage
from missionctl.core.protocols.channel import MakeFn, OpenStreamFn, RequestFn, SendFn
from missionctl.core.util.result import Result

_MISSION_TYPE_MISSION = 0
_MAV_MISSION_ACCEPTED = 0
_FRAME_GLOBAL_RELATIVE_ALT_INT = 6


@dataclass(frozen=True, slots=True)
class MissionItem:
    """One waypoint. Positions are integer degrees×1e7 / metres, matching
    MISSION_ITEM_INT on the wire (no lossy float lat/lon)."""

    seq: int
    command: int  # MAV_CMD_* (e.g. 16 = NAV_WAYPOINT)
    x: int  # latitude × 1e7
    y: int  # longitude × 1e7
    z: float  # altitude, metres (frame-relative)
    frame: int = _FRAME_GLOBAL_RELATIVE_ALT_INT
    param1: float = 0.0
    param2: float = 0.0
    param3: float = 0.0
    param4: float = 0.0
    autocontinue: int = 1
    current: int = 0


def _to_item(msg: MavlinkMessage) -> MissionItem:
    d = msg.to_dict()
    return MissionItem(
        seq=int(d["seq"]),
        command=int(d["command"]),
        x=int(d["x"]),
        y=int(d["y"]),
        z=float(d["z"]),
        frame=int(d["frame"]),
        param1=float(d["param1"]),
        param2=float(d["param2"]),
        param3=float(d["param3"]),
        param4=float(d["param4"]),
        autocontinue=int(d["autocontinue"]),
        current=int(d["current"]),
    )


class MissionProtocol:
    def __init__(
        self,
        *,
        make: MakeFn,
        send: SendFn,
        request: RequestFn,
        open_stream: OpenStreamFn,
        target: tuple[int, int],
    ) -> None:
        self._make = make
        self._send = send
        self._request = request
        self._open_stream = open_stream
        self._target = target

    async def download(
        self, *, timeout: float = 3.0, item_timeout: float = 2.0
    ) -> Result[list[MissionItem]]:
        count_req = self._make(
            "mission_request_list",
            target_system=self._target[0],
            target_component=self._target[1],
            mission_type=_MISSION_TYPE_MISSION,
        )
        try:
            count_msg = await self._request(
                count_req, lambda m: m.get_type() == "MISSION_COUNT", timeout
            )
        except TimeoutError:
            return Result(ok=False, error="timeout awaiting MISSION_COUNT")

        count = int(count_msg.to_dict()["count"])
        items: list[MissionItem] = []
        for seq in range(count):

            def is_item(m: MavlinkMessage, seq: int = seq) -> bool:
                return m.get_type() == "MISSION_ITEM_INT" and int(m.to_dict()["seq"]) == seq

            item_req = self._make(
                "mission_request_int",
                target_system=self._target[0],
                target_component=self._target[1],
                seq=seq,
                mission_type=_MISSION_TYPE_MISSION,
            )
            try:
                item_msg = await self._request(item_req, is_item, item_timeout)
            except TimeoutError:
                return Result(ok=False, error=f"timeout awaiting MISSION_ITEM_INT seq {seq}")
            items.append(_to_item(item_msg))

        await self._send(
            self._make(
                "mission_ack",
                target_system=self._target[0],
                target_component=self._target[1],
                type=_MAV_MISSION_ACCEPTED,
                mission_type=_MISSION_TYPE_MISSION,
            )
        )
        return Result(ok=True, value=items)

    async def upload(self, items: list[MissionItem], *, timeout: float = 5.0) -> Result[int]:
        stream = self._open_stream(
            lambda m: m.get_type() in ("MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_ACK")
        )
        try:
            await self._send(
                self._make(
                    "mission_count",
                    target_system=self._target[0],
                    target_component=self._target[1],
                    count=len(items),
                    mission_type=_MISSION_TYPE_MISSION,
                )
            )
            while True:
                try:
                    msg = await stream.next(timeout)
                except TimeoutError:
                    return Result(ok=False, error="timeout during mission upload handshake")
                msg_type = msg.get_type()
                if msg_type in ("MISSION_REQUEST_INT", "MISSION_REQUEST"):
                    seq = int(msg.to_dict()["seq"])
                    if not 0 <= seq < len(items):
                        return Result(ok=False, error=f"vehicle requested out-of-range seq {seq}")
                    await self._send(self._item_message(items[seq]))
                elif msg_type == "MISSION_ACK":
                    result = int(msg.to_dict()["type"])
                    if result == _MAV_MISSION_ACCEPTED:
                        return Result(ok=True, value=len(items))
                    return Result(ok=False, error=f"mission rejected: MAV_MISSION_RESULT={result}")
        finally:
            stream.close()

    async def set_current(self, seq: int, *, timeout: float = 2.0, retries: int = 3) -> Result[int]:
        def is_current(m: MavlinkMessage) -> bool:
            return m.get_type() == "MISSION_CURRENT" and int(m.to_dict()["seq"]) == seq

        for _ in range(retries):
            msg = self._make(
                "mission_set_current",
                target_system=self._target[0],
                target_component=self._target[1],
                seq=seq,
            )
            try:
                reply = await self._request(msg, is_current, timeout)
            except TimeoutError:
                continue
            return Result(ok=True, value=int(reply.to_dict()["seq"]))
        return Result(ok=False, error=f"timeout setting current waypoint {seq}")

    def _item_message(self, item: MissionItem) -> MavlinkMessage:
        return self._make(
            "mission_item_int",
            target_system=self._target[0],
            target_component=self._target[1],
            seq=item.seq,
            frame=item.frame,
            command=item.command,
            current=item.current,
            autocontinue=item.autocontinue,
            param1=item.param1,
            param2=item.param2,
            param3=item.param3,
            param4=item.param4,
            x=item.x,
            y=item.y,
            z=item.z,
            mission_type=_MISSION_TYPE_MISSION,
        )
