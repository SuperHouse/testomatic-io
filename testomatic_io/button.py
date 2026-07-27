"""
External "test start" button, active-low with an external pull-up.
"""

from . import pinout
from .gpio import digital_input


class Button:
    """Reads the external button"""

    def __init__(self):
        self._pin = None

    def init(self):
        self._pin = digital_input(pinout.BUTTON_PIN)

    def pressed(self):
        """True while the button is held down"""
        return not self._pin.value
