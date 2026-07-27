"""
IOMOD interrupt line. All IOMOD interrupts are OR'd onto a single GPIO pin
with an external pull-up, driven low by whichever module has a pending
interrupt. This only reports that *some* module needs servicing -- finding
which one is up to the caller, by polling chassis.iomod's modules.
"""

from . import pinout
from .gpio import digital_input


class Interrupts:
    """Reads the chassis-wide IOMOD interrupt line"""

    def __init__(self):
        self._pin = None

    def init(self):
        self._pin = digital_input(pinout.IOMOD_INTERRUPT_PIN)

    def is_asserted(self):
        """True if any IOMOD has a pending interrupt (line driven low)"""
        return not self._pin.value
