from missionctl.core.codec import MavlinkCodec
from missionctl.core.state import VehicleState, reduce

C = MavlinkCodec(system_id=1, component_id=1)


def test_heartbeat_armed_and_mode() -> None:
    hb = C.raw.MAVLink_heartbeat_message(
        type=2, autopilot=3, base_mode=128, custom_mode=5, system_status=4, mavlink_version=3
    )
    s = reduce(VehicleState.initial(1, 1), hb)
    assert s.armed is True
    assert s.custom_mode == 5


def test_heartbeat_disarmed() -> None:
    hb = C.raw.MAVLink_heartbeat_message(
        type=2, autopilot=3, base_mode=0, custom_mode=0, system_status=3, mavlink_version=3
    )
    assert reduce(VehicleState.initial(), hb).armed is False


def test_attitude() -> None:
    a = C.raw.MAVLink_attitude_message(
        time_boot_ms=1000, roll=0.1, pitch=-0.2, yaw=1.5, rollspeed=0, pitchspeed=0, yawspeed=0
    )
    s = reduce(VehicleState.initial(), a)
    assert s.attitude.roll_rad == 0.1
    assert s.attitude.pitch_rad == -0.2
    assert s.attitude.yaw_rad == 1.5


def test_global_position_int_normalises_units() -> None:
    g = C.raw.MAVLink_global_position_int_message(
        time_boot_ms=1000,
        lat=int(-35.363261 * 1e7),
        lon=int(149.165230 * 1e7),
        alt=584000,  # mm AMSL
        relative_alt=100000,  # mm
        vx=0,
        vy=0,
        vz=0,
        hdg=0,
    )
    s = reduce(VehicleState.initial(), g)
    assert round(s.position.lat_deg, 5) == -35.36326
    assert round(s.position.lon_deg, 5) == 149.16523
    assert s.position.alt_amsl_m == 584.0
    assert s.position.alt_rel_m == 100.0


def test_sys_status_battery_units() -> None:
    ss = C.raw.MAVLink_sys_status_message(
        onboard_control_sensors_present=0,
        onboard_control_sensors_enabled=0,
        onboard_control_sensors_health=0,
        load=250,
        voltage_battery=12600,  # mV
        current_battery=1550,  # cA
        battery_remaining=87,  # %
        drop_rate_comm=0,
        errors_comm=0,
        errors_count1=0,
        errors_count2=0,
        errors_count3=0,
        errors_count4=0,
    )
    s = reduce(VehicleState.initial(), ss)
    assert s.battery.voltage_v == 12.6
    assert s.battery.current_a == 15.5
    assert s.battery.remaining_pct == 87.0


def test_gps_raw_int() -> None:
    gp = C.raw.MAVLink_gps_raw_int_message(
        time_usec=0,
        fix_type=3,
        lat=0,
        lon=0,
        alt=0,
        eph=150,  # HDOP * 100
        epv=200,
        vel=0,
        cog=0,
        satellites_visible=11,
        alt_ellipsoid=0,
        h_acc=0,
        v_acc=0,
        vel_acc=0,
        hdg_acc=0,
        yaw=0,
    )
    s = reduce(VehicleState.initial(), gp)
    assert s.gps.fix_type == 3
    assert s.gps.satellites == 11
    assert s.gps.hdop == 1.5


def test_message_without_reducer_is_noop() -> None:
    st = C.raw.MAVLink_system_time_message(time_unix_usec=0, time_boot_ms=1234)
    s0 = VehicleState.initial(1, 1)
    assert reduce(s0, st) is s0
