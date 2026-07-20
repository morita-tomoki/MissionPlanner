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

from dataclasses import replace

from missionctl.core.state.models import Attitude, VehicleState


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
