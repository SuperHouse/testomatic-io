"""
Common interface that every IOMod expander driver must implement.

Each driver adapts a specific expander chip (AD5593R, MCP23008, Serial Wombat,
etc.) to this interface so IOMod can operate on a module without knowing what
chip is actually on it. New chip support is added by writing a driver module
that subclasses ExpanderDriver and registering it in iomod/drivers/__init__.py.
"""


class ExpanderDriver:
    """Base class for I/O expander drivers"""

    #: Human-readable chip name, used in log/print messages
    NAME = "expander"

    @classmethod
    def probe(cls, i2c_adapter, address):
        """
        Return True if this driver recognises a supported chip at `address`
        on `i2c_adapter`. Address matching is enough for chips with a fixed
        or narrow address range; chips that share an address range with
        other supported devices should read an identifying register here
        instead.
        """
        raise NotImplementedError

    def __init__(self, i2c_adapter, address):
        raise NotImplementedError

    def pin_mode(self, pin, mode):
        """Configure a pin as INPUT, OUTPUT, ADC, or DAC"""
        raise NotImplementedError

    def digital_write(self, pin, value):
        raise NotImplementedError

    def digital_read(self, pin):
        raise NotImplementedError

    def toggle(self, pin):
        raise NotImplementedError

    def analog_read(self, pin, average=1):
        raise NotImplementedError(f"{self.NAME} does not support analog input")

    def analog_write(self, pin, value):
        raise NotImplementedError(f"{self.NAME} does not support analog output")

    def read_voltage(self, pin, average=1):
        raise NotImplementedError(f"{self.NAME} does not support analog input")

    def set_vref(self, activate):
        raise NotImplementedError(f"{self.NAME} does not support a voltage reference")

    def get_vref(self):
        raise NotImplementedError(f"{self.NAME} does not support a voltage reference")

    def get_dac_range(self):
        raise NotImplementedError(f"{self.NAME} does not support DAC output")

    def set_dac_range(self, range):
        raise NotImplementedError(f"{self.NAME} does not support DAC output")

    def set_ldac_mode(self, mode):
        raise NotImplementedError(f"{self.NAME} does not support LDAC mode")

    def reset(self):
        raise NotImplementedError
