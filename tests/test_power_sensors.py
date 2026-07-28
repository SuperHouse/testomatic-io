"""
PowerSensors tests: happy-path voltage/current/power reads, and that a
missing INA260 (sensor not fitted) results in `present_* is False` and a
clear RuntimeError rather than the underlying ValueError/OSError
propagating -- see i2c_probe.py and issue #4.
"""

import pytest

import testomatic_io.power.sensors as sensors_module
from testomatic_io import pinout
from testomatic_io.power.sensors import PowerSensors


class FakeINA260:
    def __init__(self, i2c_bus, address):
        self.voltage = 3.3
        self.current = 120.0
        self.power = 396.0


class AbsentINA260:
    def __init__(self, i2c_bus, address):
        raise OSError("no device at that address")


def test_present_sensor_reads_voltage_current_power(monkeypatch):
    monkeypatch.setattr(sensors_module.adafruit_ina260, "INA260", FakeINA260)

    sensors = PowerSensors()
    sensors.init(i2c_bus=None)

    assert sensors.present_3v3 is True
    assert sensors.read_3v3() == (3.3, 120.0, 396.0)


def test_absent_sensor_reports_not_present(monkeypatch):
    monkeypatch.setattr(sensors_module.adafruit_ina260, "INA260", AbsentINA260)

    sensors = PowerSensors()
    sensors.init(i2c_bus=None)

    assert sensors.present_3v3 is False
    assert sensors.present_5v is False
    assert sensors.present_12v is False


def test_absent_sensor_raises_on_read(monkeypatch):
    monkeypatch.setattr(sensors_module.adafruit_ina260, "INA260", AbsentINA260)

    sensors = PowerSensors()
    sensors.init(i2c_bus=None)

    with pytest.raises(RuntimeError):
        sensors.read_3v3()


def test_each_rail_probed_at_its_own_address(monkeypatch):
    seen_addresses = []

    class RecordingINA260:
        def __init__(self, i2c_bus, address):
            seen_addresses.append(address)

    monkeypatch.setattr(sensors_module.adafruit_ina260, "INA260", RecordingINA260)

    sensors = PowerSensors()
    sensors.init(i2c_bus=None)

    assert seen_addresses == [
        pinout.RAIL_3V3_SENSOR_ADDRESS,
        pinout.RAIL_5V_SENSOR_ADDRESS,
        pinout.RAIL_12V_SENSOR_ADDRESS,
    ]
