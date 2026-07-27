"""
TestModule -- the swappable shim that plugs into the Chassis to interface
with a specific Device Under Test. Currently just its identity EEPROM;
expected to grow per-DUT-type drivers over time, likely identified from data
stored on that EEPROM the same way IOMOD expander chips are auto-identified
(see testomatic_io/iomod/drivers/).

Kept as an independent top-level class -- not an attribute of Chassis -- so
it can be split into its own package later without restructuring Chassis.
"""

from .eeprom import Cat24C32
from .gpio import open_i2c_bus0
from . import pinout


class TestModule:
    """Hardware abstraction for the Test Module plugged into the chassis"""

    def __init__(self):
        self.eeprom = None
        self._initialized = False

    def init(self, i2c_bus0=None):
        """
        Initialize the Test Module.

        Args:
            i2c_bus0: Optional I2C bus object for bus 0 (the identity EEPROM
                bus). Pass the same object to Chassis.init() if using both
                together, so they share one bus 0 connection. If None, a new
                bus 0 connection is opened.
        """
        if i2c_bus0 is None:
            i2c_bus0 = open_i2c_bus0()

        self.eeprom = Cat24C32(i2c_bus0, pinout.TEST_MODULE_EEPROM_ADDRESS)

        self._initialized = True
        print("Test Module initialized successfully")
