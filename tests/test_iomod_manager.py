"""
BlinkaI2CAdapter and IOModManager/tca9548a integration.

IOModManager.scan_modules()/_get_module() previously had no test coverage
at all -- only the individual drivers were tested directly. That gap is
exactly the shape of a real bug hit on real hardware (a stale, non-editable
testomatic-io install silently missing the newly-added MCP23008 driver);
the bug itself wasn't in this glue code, but nothing here would have
caught a *real* wiring mistake either, e.g. passing the wrong object to a
driver constructor or scanning the wrong channel. These tests cover that
level directly.
"""

import testomatic_io.iomod.manager as manager_module
from testomatic_io.iomod import IOModManager
from testomatic_io.iomod.drivers.ad5593r import AD5593RDriver
from testomatic_io.iomod.drivers.mcp23008 import MCP23008Driver


class FakeBlinkaBus:
    """
    Simulates a shared upstream Blinka I2C bus with the TCA9548A mux's
    control register at 0x70, an AD5593R behind channel 0, and an MCP23008
    behind channel 3 -- mirroring real IOMOD wiring (see issue with tester4,
    which had AD5593R on channels 0/2 and MCP23008 on channels 1/3).
    """

    def __init__(self):
        self.control = 0x00

    def writeto(self, address, buffer, **kwargs):
        if address == 0x70:
            self.control = buffer[0]

    def readfrom_into(self, address, buffer, **kwargs):
        if address == 0x70:
            buffer[0] = self.control

    def scan(self):
        found = [0x70]
        if self.control & (1 << 0):
            found.append(0x10)  # AD5593R on channel 0
        if self.control & (1 << 3):
            found.append(0x20)  # MCP23008 on channel 3
        return found


def test_blinka_i2c_adapter_writeto_and_readfrom_round_trip():
    bus = FakeBlinkaBus()
    adapter = manager_module.BlinkaI2CAdapter(bus)

    adapter.writeto(0x70, bytes([0x05]))

    assert bus.control == 0x05
    assert adapter.readfrom(0x70, 1) == bytes([0x05])


def test_blinka_i2c_adapter_scan_delegates_to_bus():
    bus = FakeBlinkaBus()
    bus.control = 1 << 0
    adapter = manager_module.BlinkaI2CAdapter(bus)

    assert adapter.scan() == [0x70, 0x10]


def test_scan_modules_finds_ad5593r_and_mcp23008_on_different_channels():
    iomod = IOModManager()
    iomod.init(i2c_bus=FakeBlinkaBus())

    assert iomod.scan_modules() == ["A", "D"]


def test_get_module_selects_correct_driver_per_channel():
    iomod = IOModManager()
    iomod.init(i2c_bus=FakeBlinkaBus())

    assert isinstance(iomod._get_module(0), AD5593RDriver)
    assert isinstance(iomod._get_module(3), MCP23008Driver)


def test_get_module_caches_driver_instance():
    iomod = IOModManager()
    iomod.init(i2c_bus=FakeBlinkaBus())

    first = iomod._get_module(0)
    second = iomod._get_module(0)

    assert first is second


def test_get_module_raises_for_empty_channel():
    iomod = IOModManager()
    iomod.init(i2c_bus=FakeBlinkaBus())

    try:
        iomod._get_module(5)
        raise AssertionError("expected RuntimeError for a channel with no expander")
    except RuntimeError:
        pass
