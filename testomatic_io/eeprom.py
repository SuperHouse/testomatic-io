"""
CAT24C32 I2C EEPROM driver, used for both the chassis identity EEPROM (0x50)
and the Test Module identity EEPROM (0x51) -- both on I2C bus 0. Wraps the
published adafruit-circuitpython-24lc32 package (the Microchip 24LC32 is
pin/protocol-compatible with the CAT24C32) rather than reimplementing the
24xx read/write protocol in-house, following the same reuse-over-reimplement
precedent as the AD5593R driver (see testomatic_io/iomod/drivers/ad5593r.py).
"""

from adafruit_24lc32 import EEPROM_I2C


class Cat24C32:
    """Thin wrapper around adafruit_24lc32.EEPROM_I2C for a CAT24C32 chip"""

    def __init__(self, i2c_bus, address):
        self._eeprom = EEPROM_I2C(i2c_bus, address=address)

    def read(self, address, length):
        """Read `length` bytes starting at `address`"""
        return bytes(self._eeprom[address:address + length])

    def write(self, address, data):
        """Write `data` (bytes) starting at `address`"""
        self._eeprom[address:address + len(data)] = data
