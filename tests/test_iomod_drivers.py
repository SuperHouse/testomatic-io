"""
Driver auto-detection and AD5593R register-level behaviour.

The ADC/DAC range tests guard the bug documented in
old/ad5593r/DIAGNOSIS.md: the in-house implementation this driver replaced
used the *ADC* range bit for both ADC() and DAC() pin configuration, so
DAC range control silently did nothing. The published `ad5593r` package
(and this driver) use separate set_adc_range_2x()/set_dac_range_2x() calls
-- these tests fail loudly if that ever regresses.
"""

import pytest

from testomatic_io.iomod.constants import ADC, DAC, INPUT, OUTPUT
from testomatic_io.iomod.drivers import identify_driver
from testomatic_io.iomod.drivers.ad5593r import AD5593RDriver, DEFAULT_ADDRESS


def test_identify_driver_matches_ad5593r_address():
    driver_cls, address = identify_driver(i2c_adapter=None, addresses=[DEFAULT_ADDRESS])
    assert driver_cls is AD5593RDriver
    assert address == DEFAULT_ADDRESS


def test_identify_driver_returns_none_for_unmatched_address():
    driver_cls, address = identify_driver(i2c_adapter=None, addresses=[0x77])
    assert driver_cls is None
    assert address is None


def test_identify_driver_checks_every_scanned_address():
    driver_cls, address = identify_driver(
        i2c_adapter=None, addresses=[0x77, DEFAULT_ADDRESS]
    )
    assert driver_cls is AD5593RDriver
    assert address == DEFAULT_ADDRESS


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
