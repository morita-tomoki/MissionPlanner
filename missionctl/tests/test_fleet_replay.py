from pathlib import Path

from missionctl.core.codec import MavlinkCodec
from missionctl.core.fleet import FleetManager
from missionctl.core.link.tlog_replay import TlogReplayLink


def _write_flight(path: Path) -> None:
    """A minimal telemetry burst from one vehicle (sysid 1, compid 1)."""
    c = MavlinkCodec(system_id=1, component_id=1)
    messages = [
        c.raw.MAVLink_heartbeat_message(
            type=2, autopilot=3, base_mode=128, custom_mode=4, system_status=4, mavlink_version=3
        ),
        c.raw.MAVLink_attitude_message(
            time_boot_ms=1000, roll=0.05, pitch=0.0, yaw=1.0, rollspeed=0, pitchspeed=0, yawspeed=0
        ),
        c.raw.MAVLink_global_position_int_message(
            time_boot_ms=1000,
            lat=int(-35.36 * 1e7),
            lon=int(149.16 * 1e7),
            alt=584000,
            relative_alt=50000,
            vx=0,
            vy=0,
            vz=0,
            hdg=0,
        ),
        c.raw.MAVLink_sys_status_message(
            onboard_control_sensors_present=0,
            onboard_control_sensors_enabled=0,
            onboard_control_sensors_health=0,
            load=0,
            voltage_battery=12000,
            current_battery=1000,
            battery_remaining=75,
            drop_rate_comm=0,
            errors_comm=0,
            errors_count1=0,
            errors_count2=0,
            errors_count3=0,
            errors_count4=0,
        ),
        c.raw.MAVLink_gps_raw_int_message(
            time_usec=0,
            fix_type=3,
            lat=0,
            lon=0,
            alt=0,
            eph=120,
            epv=0,
            vel=0,
            cog=0,
            satellites_visible=10,
            alt_ellipsoid=0,
            h_acc=0,
            v_acc=0,
            vel_acc=0,
            hdg_acc=0,
            yaw=0,
        ),
    ]
    buf = bytearray()
    for i, msg in enumerate(messages):
        buf += (1_000_000 * i).to_bytes(8, "big")  # 8-byte µs timestamp
        buf += c.encode(msg)
    path.write_bytes(bytes(buf))


async def test_replay_folds_telemetry_into_vehicle_state(tmp_path: Path) -> None:
    tlog = tmp_path / "flight.tlog"
    _write_flight(tlog)

    fleet = FleetManager()
    await fleet.run_link(TlogReplayLink(tlog))

    vehicle = fleet.get(1, 1)
    assert vehicle is not None
    await vehicle.wait_idle()

    st = vehicle.state.value
    assert st.armed is True
    assert st.custom_mode == 4
    assert round(st.attitude.yaw_rad, 3) == 1.0
    assert st.position.alt_rel_m == 50.0
    assert st.battery.voltage_v == 12.0
    assert st.battery.remaining_pct == 75.0
    assert st.gps.fix_type == 3
    assert st.gps.satellites == 10

    await fleet.stop()
