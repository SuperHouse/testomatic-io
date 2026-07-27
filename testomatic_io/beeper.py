"""
Piezo beeper, active-high, simple on/off (no PWM tone control).
"""

import time

from . import pinout
from .gpio import digital_output


class Beeper:
    """Controls the chassis piezo beeper"""

    def __init__(self):
        self._pin = None

    def init(self):
        self._pin = digital_output(pinout.BEEPER_PIN, initial_value=False)

    def on(self):
        self._pin.value = True

    def off(self):
        self._pin.value = False

    def beep(self, duration_s=0.1):
        """Turn the beeper on for `duration_s` seconds, then off"""
        self.on()
        time.sleep(duration_s)
        self.off()
