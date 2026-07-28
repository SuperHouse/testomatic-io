"""
Shared helper for constructing wrappers around fixed-address I2C devices
that may not actually be present on the bus (unplugged Test Module, sensor
not fitted, etc.).

CircuitPython device drivers (adafruit_24lc32.EEPROM_I2C, adafruit_ina260.INA260,
and similar) typically probe the bus inside their own __init__ and raise
ValueError/OSError if nothing responds at that address. Left uncaught, that
crashes whatever was constructing the device -- see issue #4. Every fixed,
non-swappable I2C device wrapper in this package (Cat24C32, PowerSensors)
traps that failure the same way via this helper, so callers get a `present`
flag and a clear RuntimeError instead.
"""


def probe_i2c_device(factory, address, name):
    """
    Attempt to construct an I2C device via `factory` (a zero-arg callable
    wrapping the underlying driver's constructor).

    Returns the constructed device, or None if construction failed because
    nothing responded on the bus at `address`. Any other exception is not
    trapped and propagates as-is.

    Args:
        factory: Zero-arg callable that constructs and returns the device.
        address: I2C address being probed, used only for the warning message.
        name: Human-readable device name, used only for the warning message.
    """
    try:
        return factory()
    except (ValueError, OSError) as e:
        print(f"Warning: no {name} found at 0x{address:02x}: {e}")
        return None
