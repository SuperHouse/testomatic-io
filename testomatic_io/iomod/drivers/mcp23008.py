"""
MCP23008 driver

Wraps the published `mcp23008` PyPI package (https://github.com/SuperHouse/mcp23008)
rather than reimplementing the MCP23008 register protocol in-house -- same
reuse-over-reimplement precedent as AD5593RDriver (see
testomatic_io/iomod/drivers/ad5593r.py). mcp23008 is a sibling library built
with the same injectable-transport design as ad5593r: it accepts an
injectable `i2c_bus` exposing writeto(address, buffer)/readfrom(address,
length) -- exactly what a tca9548a.TCA9548AChannel (see
testomatic_io/iomod/manager.py) provides -- so it's passed straight
through here, with no adapter needed in between.

MCP23008 is digital I/O only -- no ADC/DAC -- so pin_mode() rejects ADC/DAC
requests with a clear NotImplementedError instead of the chip silently
misbehaving. The analog-only ExpanderDriver methods (analog_read,
analog_write, read_voltage, set_vref, get_vref, get_dac_range,
set_dac_range, set_ldac_mode) are simply left unimplemented, so the base
class's own NotImplementedError (with a clear per-operation message) is
what callers see -- see issue #8.

Note: unlike the MCP23017 (same family, but 16 pins across two register
banks at different offsets), MCP23008 has a single bank of sequential
registers -- see the mcp23008 package's README for why a driver built for
one will not work against the other.
"""

from mcp23008 import MCP23008, PinMode

from ..constants import INPUT, OUTPUT, ADC, DAC
from .base import ExpanderDriver

#: I2C address the MCP23008 responds at on IOMOD hardware
DEFAULT_ADDRESS = 0x20

_PIN_MODES = {
    INPUT: PinMode.INPUT,
    OUTPUT: PinMode.OUTPUT,
}


class MCP23008Driver(ExpanderDriver):
    """ExpanderDriver adapter around the published mcp23008 package"""

    NAME = "MCP23008"
    ADDRESSES = (DEFAULT_ADDRESS,)

    @classmethod
    def probe(cls, i2c_adapter, address):
        return address in cls.ADDRESSES

    def __init__(self, i2c_adapter, address=DEFAULT_ADDRESS):
        self._chip = MCP23008(address, i2c_bus=i2c_adapter)

    def pin_mode(self, pin, mode):
        if mode == ADC:
            raise NotImplementedError(f"{self.NAME} does not support analog input")
        if mode == DAC:
            raise NotImplementedError(f"{self.NAME} does not support analog output")
        if mode not in _PIN_MODES:
            raise ValueError(f"Invalid pin mode {mode}. Use INPUT or OUTPUT.")
        self._chip.pin_mode(pin, _PIN_MODES[mode])

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

    def reset(self):
        self._chip.reset()
