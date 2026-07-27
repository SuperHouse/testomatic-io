"""
Power rail control and sensing, grouped by physical rail: turning a rail on
or off (PowerRails, GPIO relays) and measuring it (PowerSensors, INA260).
"""

from collections import namedtuple

from .rails import PowerRails
from .sensors import PowerSensors

PowerReading = namedtuple("PowerReading", ["voltage", "current", "power"])


class Power:
    """Rail-level power control and sensing for the 3.3V/5V/12V rails"""

    def __init__(self):
        self.rails = PowerRails()
        self.sensors = PowerSensors()

    def init(self, i2c_bus=None):
        self.rails.init()
        self.sensors.init(i2c_bus)

    def rail_3v3(self, on):
        """Turn the 3.3V power rail on or off"""
        self.rails.set_3v3(on)

    def rail_5v(self, on):
        """Turn the 5V power rail on or off"""
        self.rails.set_5v(on)

    def rail_12v(self, on):
        """Turn the 12V power rail on or off"""
        self.rails.set_12v(on)

    def rail_3v3_enabled(self):
        return self.rails.get_3v3()

    def rail_5v_enabled(self):
        return self.rails.get_5v()

    def rail_12v_enabled(self):
        return self.rails.get_12v()

    def read_3v3(self):
        """Read voltage (V), current (mA), and power (mW) on the 3.3V rail"""
        return PowerReading(*self.sensors.read_3v3())

    def read_5v(self):
        """Read voltage (V), current (mA), and power (mW) on the 5V rail"""
        return PowerReading(*self.sensors.read_5v())

    def read_12v(self):
        """Read voltage (V), current (mA), and power (mW) on the 12V rail"""
        return PowerReading(*self.sensors.read_12v())
