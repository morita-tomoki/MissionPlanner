"""Pure state reducers: ``(state, change) -> new_state``.

Each reducer is a small pure function that returns a new immutable snapshot. This
replaces the legacy 2,280-line ``switch`` that mutated a shared god-object under a
lock. Pure functions are trivially snapshot-testable and thread-safe by
construction.

In M2 these gain one reducer per MAVLink message type
(``reduce_heartbeat``, ``reduce_attitude``, …) dispatched by message id. For now
they demonstrate the immutable pattern and anchor the tests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from missionctl.core.codec import MavlinkMessage
from missionctl.core.state.models import Attitude, Battery, GlobalPosition, Gps, VehicleState

# MAVLink safety-armed flag in HEARTBEAT.base_mode (MAV_MODE_FLAG_SAFETY_ARMED).
_ARMED_FLAG = 0b1000_0000


# --- low-level setters (handy in unit tests / synthetic updates) --------------


def set_armed(state: VehicleState, armed: bool) -> VehicleState:
    return replace(state, armed=armed)


def set_mode(state: VehicleState, mode: str) -> VehicleState:
    return replace(state, mode=mode)


def set_attitude(
    state: VehicleState, roll_rad: float, pitch_rad: float, yaw_rad: float
) -> VehicleState:
    return replace(
        state, attitude=Attitude(roll_rad=roll_rad, pitch_rad=pitch_rad, yaw_rad=yaw_rad)
    )


# --- per-message reducers (pure: (state, msg) -> state) -----------------------
# One small function per MAVLink message type. Fields are read from the decoded
# message's dict and normalised to SI units here (mm->m, mV->V, cA->A, 1e7->deg).


def reduce_heartbeat(state: VehicleState, msg: MavlinkMessage) -> VehicleState:
    d = msg.to_dict()
    return replace(
        state,
        armed=bool(int(d["base_mode"]) & _ARMED_FLAG),
        custom_mode=int(d["custom_mode"]),
    )


def reduce_attitude(state: VehicleState, msg: MavlinkMessage) -> VehicleState:
    d = msg.to_dict()
    return replace(
        state,
        attitude=Attitude(
            roll_rad=float(d["roll"]), pitch_rad=float(d["pitch"]), yaw_rad=float(d["yaw"])
        ),
    )


def reduce_global_position_int(state: VehicleState, msg: MavlinkMessage) -> VehicleState:
    d = msg.to_dict()
    return replace(
        state,
        position=GlobalPosition(
            lat_deg=int(d["lat"]) / 1e7,
            lon_deg=int(d["lon"]) / 1e7,
            alt_amsl_m=int(d["alt"]) / 1000.0,
            alt_rel_m=int(d["relative_alt"]) / 1000.0,
        ),
    )


def reduce_sys_status(state: VehicleState, msg: MavlinkMessage) -> VehicleState:
    d = msg.to_dict()
    return replace(
        state,
        battery=Battery(
            voltage_v=int(d["voltage_battery"]) / 1000.0,
            current_a=int(d["current_battery"]) / 100.0,
            remaining_pct=float(d["battery_remaining"]),
        ),
    )


def reduce_gps_raw_int(state: VehicleState, msg: MavlinkMessage) -> VehicleState:
    d = msg.to_dict()
    return replace(
        state,
        gps=Gps(
            fix_type=int(d["fix_type"]),
            satellites=int(d["satellites_visible"]),
            hdop=int(d["eph"]) / 100.0,
        ),
    )


_REDUCERS: dict[str, Callable[[VehicleState, MavlinkMessage], VehicleState]] = {
    "HEARTBEAT": reduce_heartbeat,
    "ATTITUDE": reduce_attitude,
    "GLOBAL_POSITION_INT": reduce_global_position_int,
    "SYS_STATUS": reduce_sys_status,
    "GPS_RAW_INT": reduce_gps_raw_int,
}


def reduce(state: VehicleState, msg: MavlinkMessage) -> VehicleState:
    """Apply the reducer for ``msg``'s type, or return ``state`` unchanged if no
    reducer is registered for that message type."""
    fn = _REDUCERS.get(msg.get_type())
    return fn(state, msg) if fn is not None else state
