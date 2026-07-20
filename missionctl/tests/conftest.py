import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "sitl: end-to-end test requiring ArduPilot SITL (excluded from the default "
        "headless `make check`; run via `make sitl`).",
    )
