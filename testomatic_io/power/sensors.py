"""
INA260 power sensors for the 3.3V/5V/12V rails. These sit directly on I2C
bus 1 at fixed addresses, NOT behind the TCA9548A mux, so they're reachable
at any time regardless of IOMOD state.
"""

import board
import adafruit_ina260

from .. import pinout
from ..i2c_probe import probe_i2c_device


class PowerSensors:
    """INA260-based voltage/current/power sensing for the chassis power rails"""

    def __init__(self):
        self._sensor_3v3 = None
        self._sensor_5v = None
        self._sensor_12v = None

    def init(self, i2c_bus=None):
        if i2c_bus is None:
            i2c_bus = board.I2C()
        self._sensor_3v3 = probe_i2c_device(
            lambda: adafruit_ina260.INA260(i2c_bus, pinout.RAIL_3V3_SENSOR_ADDRESS),
            pinout.RAIL_3V3_SENSOR_ADDRESS, "INA260 sensor (3.3V rail)",
        )
        self._sensor_5v = probe_i2c_device(
            lambda: adafruit_ina260.INA260(i2c_bus, pinout.RAIL_5V_SENSOR_ADDRESS),
            pinout.RAIL_5V_SENSOR_ADDRESS, "INA260 sensor (5V rail)",
        )
        self._sensor_12v = probe_i2c_device(
            lambda: adafruit_ina260.INA260(i2c_bus, pinout.RAIL_12V_SENSOR_ADDRESS),
            pinout.RAIL_12V_SENSOR_ADDRESS, "INA260 sensor (12V rail)",
        )

    @property
    def present_3v3(self):
        """True if the 3.3V rail's INA260 sensor was detected on the bus"""
        return self._sensor_3v3 is not None

    @property
    def present_5v(self):
        """True if the 5V rail's INA260 sensor was detected on the bus"""
        return self._sensor_5v is not None

    @property
    def present_12v(self):
        """True if the 12V rail's INA260 sensor was detected on the bus"""
        return self._sensor_12v is not None

    def read_3v3(self):
        """Returns (voltage_v, current_ma, power_mw)"""
        if self._sensor_3v3 is None:
            raise RuntimeError("No INA260 sensor present for the 3.3V rail")
        return self._sensor_3v3.voltage, self._sensor_3v3.current, self._sensor_3v3.power

    def read_5v(self):
        """Returns (voltage_v, current_ma, power_mw)"""
        if self._sensor_5v is None:
            raise RuntimeError("No INA260 sensor present for the 5V rail")
        return self._sensor_5v.voltage, self._sensor_5v.current, self._sensor_5v.power

    def read_12v(self):
        """Returns (voltage_v, current_ma, power_mw)"""
        if self._sensor_12v is None:
            raise RuntimeError("No INA260 sensor present for the 12V rail")
        return self._sensor_12v.voltage, self._sensor_12v.current, self._sensor_12v.power
