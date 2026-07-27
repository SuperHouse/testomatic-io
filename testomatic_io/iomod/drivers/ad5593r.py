"""
AD5593R driver

Wraps the published `ad5593r` PyPI package (>=0.3.0) rather than
reimplementing the AD5593R register protocol in-house. Earlier versions of
that package always opened their own smbus2 connection scoped to a Linux
bus number, with no way to accept an external transport, so it couldn't be
routed through the TCA9548A multiplexer's per-channel addressing. As of
ad5593r 0.2.0 it accepts an injectable `i2c_bus` exposing
writeto(address, buffer)/readfrom(address, length) -- exactly what
ChannelI2CAdapter provides -- so it's passed straight through here.

Original by Tristan Muller for MicroPython (https://101robotics.com), then
ported to an in-house Python 3 implementation by Jonathan Oxer; this driver
now delegates that protocol work to the ad5593r package instead.
"""

import time  # For the post-reset recovery delay

from ad5593r import AD5593R, PinMode

from ..constants import INPUT, OUTPUT, ADC, DAC
from .base import ExpanderDriver

#: I2C address the AD5593R responds at on IOMOD hardware
DEFAULT_ADDRESS = 0x10

_PIN_MODES = {
    INPUT: PinMode.INPUT,
    OUTPUT: PinMode.OUTPUT,
}


class AD5593RDriver(ExpanderDriver):
    """ExpanderDriver adapter around the published ad5593r package"""

    NAME = "AD5593R"
    ADDRESSES = (DEFAULT_ADDRESS,)

    @classmethod
    def probe(cls, i2c_adapter, address):
        return address in cls.ADDRESSES

    def __init__(self, i2c_adapter, address=DEFAULT_ADDRESS):
        self._chip = AD5593R(address, i2c_bus=i2c_adapter)
        # DAC range is a chip-wide setting (not per-pin); tracked here so
        # get_dac_range() can report it back and pin_mode(DAC) can reapply
        # it without needing a package-level getter.
        self._dac_range = 2  # 2x Vref, matching this driver's historical default

    def pin_mode(self, pin, mode):
        if mode == ADC:
            self._chip.pin_mode(pin, PinMode.ADC)
            self._chip.set_external_reference(False, 2.5)  # ensure internal Vref is active
            self._chip.set_adc_range_2x(False)  # 1x Vref, matching this driver's historical default
        elif mode == DAC:
            self._chip.pin_mode(pin, PinMode.DAC)
            self._chip.set_external_reference(False, 2.5)  # ensure internal Vref is active
            self._chip.set_dac_range_2x(self._dac_range == 2)
        elif mode in _PIN_MODES:
            self._chip.pin_mode(pin, _PIN_MODES[mode])
        else:
            raise ValueError(f"Invalid pin mode {mode}. Use INPUT, OUTPUT, ADC, or DAC.")

    def digital_write(self, pin, value):
        self._chip.pin_mode(pin, PinMode.OUTPUT)
        self._chip.digital_write(pin, value)

    def digital_read(self, pin):
        self._chip.pin_mode(pin, PinMode.INPUT)
        return self._chip.digital_read(pin)

    def toggle(self, pin):
        self._chip.pin_mode(pin, PinMode.OUTPUT)
        current = self._chip.digital_read(pin)
        self._chip.digital_write(pin, 0 if current else 1)

    def analog_read(self, pin, average=1):
        self.pin_mode(pin, ADC)
        values = [self._chip.analog_read(pin) for _ in range(max(1, average))]
        return int(sum(values) / len(values))

    def analog_write(self, pin, value):
        # Caller is expected to have already configured the pin as DAC via
        # pin_mode(), matching this driver's long-standing behaviour.
        self._chip.analog_write(pin, value)

    def read_voltage(self, pin, average=1):
        vref = self._chip.get_vref()
        value = self.analog_read(pin, average)
        return (value / 4096) * vref

    def set_vref(self, activate):
        # AD5593R hardware here only ever uses the internal 2.5V reference;
        # "activate" selects it, "deactivate" switches to (unconfigured)
        # external reference -- there's no voltage to supply for that case.
        self._chip.set_external_reference(not activate, 2.5)

    def get_vref(self):
        return self._chip.get_vref()

    def get_dac_range(self):
        return self._dac_range

    def set_dac_range(self, range):
        self._dac_range = range
        self._chip.set_dac_range_2x(range == 2)

    def set_ldac_mode(self, mode):
        self._chip.set_ldac_mode(mode)

    def reset(self):
        self._chip.reset()
        time.sleep(0.1)  # Datasheet-recommended delay for the device to recover
