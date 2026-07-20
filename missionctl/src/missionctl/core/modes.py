"""ArduPlane flight modes.

Control target is Plane only (ADR-0005). These are the ``custom_mode`` values
carried in HEARTBEAT and used by ``MAV_CMD_DO_SET_MODE``. Kept in core because
``set_mode`` needs the name→number mapping; the display layer can reuse the
reverse map for labels. (Rover display names and any other vehicle types are a
separate, later, display-side concern.)
"""

from __future__ import annotations

PLANE_MODES: dict[str, int] = {
    "MANUAL": 0,
    "CIRCLE": 1,
    "STABILIZE": 2,
    "TRAINING": 3,
    "ACRO": 4,
    "FBWA": 5,
    "FBWB": 6,
    "CRUISE": 7,
    "AUTOTUNE": 8,
    "AUTO": 10,
    "RTL": 11,
    "LOITER": 12,
    "TAKEOFF": 13,
    "AVOID_ADSB": 14,
    "GUIDED": 15,
    "INITIALISING": 16,
    "QSTABILIZE": 17,
    "QHOVER": 18,
    "QLOITER": 19,
    "QLAND": 20,
    "QRTL": 21,
    "QAUTOTUNE": 22,
    "QACRO": 23,
    "THERMAL": 24,
    "LOITER_ALT_QLAND": 25,
}

PLANE_MODE_NAMES: dict[int, str] = {number: name for name, number in PLANE_MODES.items()}


def plane_mode_name(custom_mode: int) -> str:
    """Human-readable Plane mode name, or ``MODE(n)`` if unknown."""
    return PLANE_MODE_NAMES.get(custom_mode, f"MODE({custom_mode})")
