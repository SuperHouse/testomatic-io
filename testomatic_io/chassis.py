"""
Chassis -- the fixed Testomatic enclosure: IOMODs, power rail control and
sensing, the IOMOD interrupt line, the external button, the piezo beeper,
and the chassis identity EEPROM.

Does NOT include the Test Module (see testomatic_io.test_module.TestModule)
-- that's a separate, swappable physical device that plugs into the chassis.
"""

import board

from .iomod import IOModManager
from .power import Power
from .interrupts import Interrupts
from .button import Button
from .beeper import Beeper
from .eeprom import Cat24C32
from .gpio import open_i2c_bus0
from . import pinout


class Chassis:
    """Hardware abstraction for the fixed Testomatic chassis"""

    def __init__(self):
        self.iomod = IOModManager()
        self.power = Power()
        self.interrupts = Interrupts()
        self.button = Button()
        self.beeper = Beeper()
        self.hat_eeprom = None
        self._initialized = False

    def init(self, i2c_bus=None, i2c_bus0=None):
        """
        Initialize every chassis subsystem.

        Args:
            i2c_bus: Optional I2C bus object for bus 1 (IOMODs + power
                sensors). If None, uses board.I2C().
            i2c_bus0: Optional I2C bus object for bus 0 (the identity EEPROM
                bus). Pass the same object to TestModule.init() if using both
                together, so they share one bus 0 connection. If None, a new
                bus 0 connection is opened.
        """
        if i2c_bus is None:
            i2c_bus = board.I2C()
        if i2c_bus0 is None:
            i2c_bus0 = open_i2c_bus0()

        self.iomod.init(i2c_bus)
        self.power.init(i2c_bus)
        self.interrupts.init()
        self.button.init()
        self.beeper.init()
        self.hat_eeprom = Cat24C32(i2c_bus0, pinout.CHASSIS_EEPROM_ADDRESS)

        self._initialized = True
        print("Chassis initialized successfully")
