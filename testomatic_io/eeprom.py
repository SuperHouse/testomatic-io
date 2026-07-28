"""
CAT24C32 I2C EEPROM driver, used for both the chassis identity EEPROM (0x50)
and the Test Module identity EEPROM (0x51) -- both on I2C bus 0. Wraps the
published adafruit-circuitpython-24lc32 package (the Microchip 24LC32 is
pin/protocol-compatible with the CAT24C32) rather than reimplementing the
24xx read/write protocol in-house, following the same reuse-over-reimplement
precedent as the AD5593R driver (see testomatic_io/iomod/drivers/ad5593r.py).
"""

from adafruit_24lc32 import EEPROM_I2C

from .i2c_probe import probe_i2c_device


class Cat24C32:
    """
    Thin wrapper around adafruit_24lc32.EEPROM_I2C for a CAT24C32 chip.

    Construction probes the chip on the bus; if nothing responds at
    `address` (unplugged Test Module, missing chassis EEPROM, etc.) the
    probe failure is trapped (see testomatic_io/i2c_probe.py) and `present`
    is False instead of the ValueError/OSError from adafruit_bus_device
    propagating out and crashing whatever was initializing at the time.
    """

    def __init__(self, i2c_bus, address):
        self._address = address
        self._eeprom = probe_i2c_device(
            lambda: EEPROM_I2C(i2c_bus, address=address), address, "EEPROM"
        )

    @property
    def present(self):
        """True if the EEPROM was detected on the bus at construction time"""
        return self._eeprom is not None

    def read(self, address, length):
        """Read `length` bytes starting at `address`"""
        if self._eeprom is None:
            raise RuntimeError(f"No EEPROM present at 0x{self._address:02x}")
        return bytes(self._eeprom[address:address + length])

    def write(self, address, data):
        """Write `data` (bytes) starting at `address`"""
        if self._eeprom is None:
            raise RuntimeError(f"No EEPROM present at 0x{self._address:02x}")
        self._eeprom[address:address + len(data)] = data
