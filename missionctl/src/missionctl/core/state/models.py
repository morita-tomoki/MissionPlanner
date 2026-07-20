"""Immutable vehicle state, in SI units only.

Every field is frozen. Unit conversion, display formatting, speech, and UI banners
belong in the Qt/ViewModel layer — never here. (The legacy ``CurrentState`` baked
process-wide unit multipliers and TTS into the model, so you couldn't read raw
telemetry without undoing a global setting. We keep the model pure.)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Attitude:
    roll_rad: float = 0.0
    pitch_rad: float = 0.0
    yaw_rad: float = 0.0


@dataclass(frozen=True, slots=True)
class GlobalPosition:
    lat_deg: float = 0.0
    lon_deg: float = 0.0
    alt_amsl_m: float = 0.0
    alt_rel_m: float = 0.0


@dataclass(frozen=True, slots=True)
class Battery:
    voltage_v: float = 0.0
    current_a: float = 0.0
    remaining_pct: float = 0.0


@dataclass(frozen=True, slots=True)
class VehicleState:
    sysid: int = 0
    compid: int = 0
    armed: bool = False
    mode: str = "UNKNOWN"
    attitude: Attitude = field(default_factory=Attitude)
    position: GlobalPosition = field(default_factory=GlobalPosition)
    battery: Battery = field(default_factory=Battery)

    @staticmethod
    def initial(sysid: int = 0, compid: int = 0) -> VehicleState:
        return VehicleState(sysid=sysid, compid=compid)
