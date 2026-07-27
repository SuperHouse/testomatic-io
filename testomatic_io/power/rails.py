"""
GPIO relay control for the 3.3V/5V/12V power rails supplied to the Device
Under Test. All three relays are active-high RPi GPIO outputs.
"""

from .. import pinout
from ..gpio import digital_output


class PowerRails:
    """Relay control for the chassis power rails"""

    def __init__(self):
        self._rail_3v3 = None
        self._rail_5v = None
        self._rail_12v = None

    def init(self):
        self._rail_3v3 = digital_output(pinout.RAIL_3V3_RELAY_PIN, initial_value=False)
        self._rail_5v = digital_output(pinout.RAIL_5V_RELAY_PIN, initial_value=False)
        self._rail_12v = digital_output(pinout.RAIL_12V_RELAY_PIN, initial_value=False)

    def set_3v3(self, on):
        self._rail_3v3.value = on

    def set_5v(self, on):
        self._rail_5v.value = on

    def set_12v(self, on):
        self._rail_12v.value = on

    def get_3v3(self):
        return self._rail_3v3.value

    def get_5v(self):
        return self._rail_5v.value

    def get_12v(self):
        return self._rail_12v.value
