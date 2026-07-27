"""
INA260 power sensors for the 3.3V/5V/12V rails. These sit directly on I2C
bus 1 at fixed addresses, NOT behind the TCA9548A mux, so they're reachable
at any time regardless of IOMOD state.
"""

import board
import adafruit_ina260

from .. import pinout


class PowerSensors:
    """INA260-based voltage/current/power sensing for the chassis power rails"""

    def __init__(self):
        self._sensor_3v3 = None
        self._sensor_5v = None
        self._sensor_12v = None

    def init(self, i2c_bus=None):
        if i2c_bus is None:
            i2c_bus = board.I2C()
        self._sensor_3v3 = adafruit_ina260.INA260(i2c_bus, pinout.RAIL_3V3_SENSOR_ADDRESS)
        self._sensor_5v = adafruit_ina260.INA260(i2c_bus, pinout.RAIL_5V_SENSOR_ADDRESS)
        self._sensor_12v = adafruit_ina260.INA260(i2c_bus, pinout.RAIL_12V_SENSOR_ADDRESS)

    def read_3v3(self):
        """Returns (voltage_v, current_ma, power_mw)"""
        return self._sensor_3v3.voltage, self._sensor_3v3.current, self._sensor_3v3.power

    def read_5v(self):
        """Returns (voltage_v, current_ma, power_mw)"""
        return self._sensor_5v.voltage, self._sensor_5v.current, self._sensor_5v.power

    def read_12v(self):
        """Returns (voltage_v, current_ma, power_mw)"""
        return self._sensor_12v.voltage, self._sensor_12v.current, self._sensor_12v.power
