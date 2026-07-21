from missionctl.core.modes import PLANE_MODES, plane_mode_name


def test_known_modes() -> None:
    assert PLANE_MODES["MANUAL"] == 0
    assert PLANE_MODES["GUIDED"] == 15
    assert PLANE_MODES["RTL"] == 11


def test_name_lookup() -> None:
    assert plane_mode_name(11) == "RTL"
    assert plane_mode_name(0) == "MANUAL"


def test_unknown_number() -> None:
    assert plane_mode_name(999) == "MODE(999)"
