"""
Cat24C32 tests: happy-path read/write, and that a probe failure (nothing
responds on the bus -- unplugged Test Module, missing chassis EEPROM)
results in `present is False` and a clear RuntimeError rather than the
underlying ValueError/OSError propagating -- see i2c_probe.py and issue #4.
"""

import pytest

import testomatic_io.eeprom as eeprom_module
from testomatic_io.eeprom import Cat24C32


class FakeEEPROM_I2C:
    """Backed by a plain bytearray, supporting the same slice read/write
    Cat24C32 uses against the real adafruit_24lc32.EEPROM_I2C."""

    def __init__(self, i2c_bus, address):
        self._data = bytearray(4096)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value


class AbsentEEPROM_I2C:
    def __init__(self, i2c_bus, address):
        raise OSError("no device at that address")


def test_present_and_read_write_round_trip(monkeypatch):
    monkeypatch.setattr(eeprom_module, "EEPROM_I2C", FakeEEPROM_I2C)

    eeprom = Cat24C32(i2c_bus=None, address=0x50)

    assert eeprom.present is True
    eeprom.write(0, b"hello")
    assert eeprom.read(0, 5) == b"hello"


def test_absent_eeprom_reports_not_present(monkeypatch):
    monkeypatch.setattr(eeprom_module, "EEPROM_I2C", AbsentEEPROM_I2C)

    eeprom = Cat24C32(i2c_bus=None, address=0x51)

    assert eeprom.present is False


def test_absent_eeprom_raises_on_read_and_write(monkeypatch):
    monkeypatch.setattr(eeprom_module, "EEPROM_I2C", AbsentEEPROM_I2C)

    eeprom = Cat24C32(i2c_bus=None, address=0x51)

    with pytest.raises(RuntimeError):
        eeprom.read(0, 5)
    with pytest.raises(RuntimeError):
        eeprom.write(0, b"x")
