"""
Driver registry for supported I/O expander chips.

Modules are identified automatically: IOMod scans each TCA9548A channel for
I2C addresses and asks each registered driver whether it recognises one of
them. To add support for a new expander chip, write a driver module (see
ad5593r.py for the pattern) and add its class to DRIVERS below.
"""

from .base import ExpanderDriver
from .ad5593r import AD5593RDriver

# Ordered list of supported driver classes, checked in order for each
# I2C address found on a channel.
DRIVERS = [
    AD5593RDriver,
]


def identify_driver(i2c_adapter, addresses):
    """
    Identify which registered driver (if any) matches one of `addresses`,
    found by scanning a module's I2C channel.

    Returns:
        (driver_class, address) for the first match, or (None, None)
    """
    for address in addresses:
        for driver_cls in DRIVERS:
            if driver_cls.probe(i2c_adapter, address):
                return driver_cls, address
    return None, None
