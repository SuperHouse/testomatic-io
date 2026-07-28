"""
Driver auto-detection, and AD5593R/MCP23008 register-level behaviour.

The ADC/DAC range tests guard the bug documented in
old/ad5593r/DIAGNOSIS.md: the in-house implementation this driver replaced
used the *ADC* range bit for both ADC() and DAC() pin configuration, so
DAC range control silently did nothing. The published `ad5593r` package
(and this driver) use separate set_adc_range_2x()/set_dac_range_2x() calls
-- these tests fail loudly if that ever regresses.

The MCP23008 tests guard issue #8's requirement that analog operations
fail gracefully on a digital-only chip, rather than misbehaving silently.
"""

import pytest

from testomatic_io.iomod.constants import ADC, DAC, INPUT, OUTPUT
from testomatic_io.iomod.drivers import identify_driver
from testomatic_io.iomod.drivers.ad5593r import AD5593RDriver, DEFAULT_ADDRESS as AD5593R_ADDRESS
from testomatic_io.iomod.drivers.mcp23008 import MCP23008Driver, DEFAULT_ADDRESS as MCP23008_ADDRESS


def test_identify_driver_matches_ad5593r_address():
    driver_cls, address = identify_driver(i2c_adapter=None, addresses=[AD5593R_ADDRESS])
    assert driver_cls is AD5593RDriver
    assert address == AD5593R_ADDRESS


def test_identify_driver_returns_none_for_unmatched_address():
    driver_cls, address = identify_driver(i2c_adapter=None, addresses=[0x77])
    assert driver_cls is None
    assert address is None


def test_identify_driver_checks_every_scanned_address():
    driver_cls, address = identify_driver(
        i2c_adapter=None, addresses=[0x77, AD5593R_ADDRESS]
    )
    assert driver_cls is AD5593RDriver
    assert address == AD5593R_ADDRESS


def test_dac_pin_mode_sets_dac_range_not_adc_range():
    driver = AD5593RDriver(i2c_adapter=None)

    driver.pin_mode(3, DAC)

    driver._chip.set_dac_range_2x.assert_called_once()
    driver._chip.set_adc_range_2x.assert_not_called()


def test_adc_pin_mode_sets_adc_range_not_dac_range():
    driver = AD5593RDriver(i2c_adapter=None)

    driver.pin_mode(3, ADC)

    driver._chip.set_adc_range_2x.assert_called_once()
    driver._chip.set_dac_range_2x.assert_not_called()


def test_input_output_pin_modes_do_not_touch_range_bits():
    driver = AD5593RDriver(i2c_adapter=None)

    driver.pin_mode(3, INPUT)
    driver.pin_mode(3, OUTPUT)

    driver._chip.set_adc_range_2x.assert_not_called()
    driver._chip.set_dac_range_2x.assert_not_called()


def test_invalid_pin_mode_raises():
    driver = AD5593RDriver(i2c_adapter=None)
    with pytest.raises(ValueError):
        driver.pin_mode(3, "not-a-mode")


def test_identify_driver_matches_mcp23008_address():
    driver_cls, address = identify_driver(i2c_adapter=None, addresses=[MCP23008_ADDRESS])
    assert driver_cls is MCP23008Driver
    assert address == MCP23008_ADDRESS


def test_identify_driver_distinguishes_ad5593r_and_mcp23008():
    """Each address must resolve to its own driver, not cross-match --
    0x10 is AD5593R-only, 0x20 is MCP23008-only -- regardless of which
    order the scanned addresses are checked in."""
    driver_cls, address = identify_driver(
        i2c_adapter=None, addresses=[MCP23008_ADDRESS, AD5593R_ADDRESS]
    )
    assert driver_cls is MCP23008Driver
    assert address == MCP23008_ADDRESS

    driver_cls, address = identify_driver(
        i2c_adapter=None, addresses=[AD5593R_ADDRESS, MCP23008_ADDRESS]
    )
    assert driver_cls is AD5593RDriver
    assert address == AD5593R_ADDRESS


def test_mcp23008_digital_write_read_round_trip():
    driver = MCP23008Driver(i2c_adapter=None)

    driver.digital_write(2, 1)

    driver._chip.pin_mode.assert_called_with(2, "OUTPUT")
    driver._chip.digital_write.assert_called_once_with(2, 1)

    driver._chip.digital_read.return_value = 1
    assert driver.digital_read(2) == 1
    driver._chip.pin_mode.assert_called_with(2, "INPUT")


def test_mcp23008_toggle_flips_current_value():
    driver = MCP23008Driver(i2c_adapter=None)
    driver._chip.digital_read.return_value = 0

    driver.toggle(4)

    driver._chip.digital_write.assert_called_once_with(4, 1)


def test_mcp23008_pin_mode_adc_raises_not_implemented():
    driver = MCP23008Driver(i2c_adapter=None)
    with pytest.raises(NotImplementedError):
        driver.pin_mode(3, ADC)


def test_mcp23008_pin_mode_dac_raises_not_implemented():
    driver = MCP23008Driver(i2c_adapter=None)
    with pytest.raises(NotImplementedError):
        driver.pin_mode(3, DAC)


def test_mcp23008_analog_operations_fail_gracefully():
    """Not overridden by MCP23008Driver, so these fall through to
    ExpanderDriver's base implementation -- issue #8's "fail gracefully"
    requirement for a digital-only chip."""
    driver = MCP23008Driver(i2c_adapter=None)
    with pytest.raises(NotImplementedError):
        driver.analog_read(3)
    with pytest.raises(NotImplementedError):
        driver.analog_write(3, 100)
    with pytest.raises(NotImplementedError):
        driver.read_voltage(3)
    with pytest.raises(NotImplementedError):
        driver.set_vref(True)
    with pytest.raises(NotImplementedError):
        driver.get_dac_range()


def test_mcp23008_invalid_pin_mode_raises_value_error():
    driver = MCP23008Driver(i2c_adapter=None)
    with pytest.raises(ValueError):
        driver.pin_mode(3, "not-a-mode")


def test_mcp23008_reset_calls_through_to_chip():
    driver = MCP23008Driver(i2c_adapter=None)
    driver.reset()
    driver._chip.reset.assert_called_once()
