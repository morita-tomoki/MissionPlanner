from missionctl.core.state import reducers
from missionctl.core.state.models import VehicleState


def test_reducers_are_pure_and_immutable() -> None:
    s0 = VehicleState.initial(sysid=1, compid=1)
    s1 = reducers.set_armed(s0, True)
    assert s0.armed is False  # original left untouched
    assert s1.armed is True
    assert s1.sysid == 1 and s1.compid == 1


def test_set_mode() -> None:
    s0 = VehicleState.initial()
    s1 = reducers.set_mode(s0, "GUIDED")
    assert s1.mode == "GUIDED"
    assert s0.mode == "UNKNOWN"


def test_set_attitude() -> None:
    s0 = VehicleState.initial()
    s1 = reducers.set_attitude(s0, 0.1, 0.2, 0.3)
    assert (s1.attitude.roll_rad, s1.attitude.pitch_rad, s1.attitude.yaw_rad) == (0.1, 0.2, 0.3)
    assert s0.attitude.roll_rad == 0.0  # unchanged


def test_state_is_frozen() -> None:
    s = VehicleState.initial()
    import dataclasses

    try:
        s.armed = True  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("VehicleState must be immutable")
