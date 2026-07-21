"""Parameter protocol: read one, set one, and download the full set.

get/set are one-shot request/reply (PARAM_REQUEST_READ / PARAM_SET, each
confirmed by a matching PARAM_VALUE). download_all streams the whole table
(PARAM_REQUEST_LIST → N × PARAM_VALUE), reporting progress and finishing when the
advertised param_count is reached or the stream goes idle.
"""

from __future__ import annotations

from collections.abc import Callable

from missionctl.core.codec import MavlinkMessage
from missionctl.core.protocols.channel import MakeFn, OpenStreamFn, RequestFn, SendFn
from missionctl.core.util.result import Result

# ArduPilot transports all parameters as float32 over MAVLink.
_MAV_PARAM_TYPE_REAL32 = 9

ProgressFn = Callable[[float], None]


def _clean_param_id(raw: object) -> str:
    """PARAM_VALUE.param_id is a fixed 16-char field; normalise to a plain str."""
    if isinstance(raw, bytes):
        raw = raw.decode("ascii", "ignore")
    return str(raw).split("\x00")[0]


class ParamProtocol:
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

    async def get(self, name: str, *, timeout: float = 2.0, retries: int = 3) -> Result[float]:
        def is_value(m: MavlinkMessage) -> bool:
            return (
                m.get_type() == "PARAM_VALUE" and _clean_param_id(m.to_dict()["param_id"]) == name
            )

        for _ in range(retries):
            msg = self._make(
                "param_request_read",
                target_system=self._target[0],
                target_component=self._target[1],
                param_id=name.encode(),
                param_index=-1,
            )
            try:
                reply = await self._request(msg, is_value, timeout)
            except TimeoutError:
                continue
            return Result(ok=True, value=float(reply.to_dict()["param_value"]))
        return Result(ok=False, error=f"timeout reading param {name}")

    async def set(
        self, name: str, value: float, *, timeout: float = 2.0, retries: int = 3
    ) -> Result[float]:
        def is_value(m: MavlinkMessage) -> bool:
            return (
                m.get_type() == "PARAM_VALUE" and _clean_param_id(m.to_dict()["param_id"]) == name
            )

        for _ in range(retries):
            msg = self._make(
                "param_set",
                target_system=self._target[0],
                target_component=self._target[1],
                param_id=name.encode(),
                param_value=float(value),
                param_type=_MAV_PARAM_TYPE_REAL32,
            )
            try:
                reply = await self._request(msg, is_value, timeout)
            except TimeoutError:
                continue
            return Result(ok=True, value=float(reply.to_dict()["param_value"]))
        return Result(ok=False, error=f"timeout setting param {name}")

    async def download_all(
        self,
        *,
        progress: ProgressFn | None = None,
        idle_timeout: float = 3.0,
    ) -> Result[dict[str, float]]:
        """Download the whole parameter table. Completes when param_count values
        have arrived, or fails if the stream goes idle before that.
        (Re-requesting individual dropped indices is a future refinement.)"""
        params: dict[str, float] = {}
        expected: int | None = None
        stream = self._open_stream(lambda m: m.get_type() == "PARAM_VALUE")
        try:
            await self._send(
                self._make(
                    "param_request_list",
                    target_system=self._target[0],
                    target_component=self._target[1],
                )
            )
            while True:
                try:
                    msg = await stream.next(idle_timeout)
                except TimeoutError:
                    break
                d = msg.to_dict()
                params[_clean_param_id(d["param_id"])] = float(d["param_value"])
                expected = int(d["param_count"])
                if progress is not None and expected > 0:
                    progress(min(1.0, len(params) / expected))
                if expected > 0 and len(params) >= expected:
                    break
        finally:
            stream.close()

        if expected is None:
            return Result(ok=False, error="no PARAM_VALUE received")
        if len(params) < expected:
            return Result(ok=False, error=f"incomplete: {len(params)}/{expected} params")
        return Result(ok=True, value=params)
