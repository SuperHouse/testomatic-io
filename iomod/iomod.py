#!/usr/bin/env python3
"""
IOMod Library - Wrapper for I/O Expander Modules with TCA9548A Multiplexer Support

This library provides a high-level interface for controlling multiple I/O
expander modules (e.g. AD5593R, MCP23008) through a TCA9548A I2C multiplexer.
It allows you to select a specific module and then perform digital/analog
operations on that module. The expander chip on each module is identified
automatically by its I2C address; see iomod/drivers/ for supported chips and
how to add new ones.

Usage example:
    import iomod

    # Initialize the IOMod system
    iomod.init()

    # Select module D and write HIGH to pin 4
    iomod.digitalwrite('D', 4, iomod.HIGH)

    # Select module C and read from pin 1
    value = iomod.digitalread('C', 1)

    # Select module B and read analog value from pin 3
    voltage = iomod.analogread('B', 3)

Modules can be referenced either by letter ('A'-'H', preferred) or by their
underlying numeric channel (0-7) on the TCA9548A multiplexer.
"""

import board
import adafruit_tca9548a

from .constants import HIGH, LOW, INPUT, OUTPUT, ADC, DAC
from .drivers import identify_driver

# Module identifiers: TCA9548A channels 0-7 map to letters 'A'-'H'
_MODULE_LETTERS = "ABCDEFGH"

def _module_index(module_id):
    """
    Convert a module identifier to its numeric channel index (0-7)

    Args:
        module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
    """
    if isinstance(module_id, str):
        if len(module_id) != 1 or module_id.upper() not in _MODULE_LETTERS:
            raise ValueError(f"Invalid module '{module_id}'. Must be a letter A-H.")
        return _MODULE_LETTERS.index(module_id.upper())
    return module_id

def _module_letter(module_id):
    """Convert a numeric channel index (0-7) to its module letter ('A'-'H')"""
    return _MODULE_LETTERS[module_id]

class ChannelI2CAdapter:
    """
    Adapter to provide the readfrom/writeto/scan API expected by expander
    drivers over a CircuitPython TCA9548A channel, which exposes
    readfrom_into/writeto. Each call acquires/releases the I2C lock to be
    safe across operations.
    """
    def __init__(self, channel):
        self._ch = channel
    
    def _with_lock(self):
        # Context manager to acquire/release lock even if exceptions occur
        class _LockCtx:
            def __init__(self, ch):
                self._ch = ch
                self._locked = False
            def __enter__(self):
                if hasattr(self._ch, 'try_lock'):
                    self._locked = self._ch.try_lock()
                return self
            def __exit__(self, exc_type, exc, tb):
                if self._locked and hasattr(self._ch, 'unlock'):
                    self._ch.unlock()
        return _LockCtx(self._ch)
    
    def scan(self):
        with self._with_lock():
            if hasattr(self._ch, 'scan'):
                return self._ch.scan()
            return []
    
    def writeto(self, address, data):
        # Normalize data to bytes
        if isinstance(data, int):
            data = bytes([data])
        else:
            data = bytes(data)
        with self._with_lock():
            # CircuitPython API: writeto(address, buffer, *, start=0, end=None, stop=True)
            self._ch.writeto(address, data)
    
    def readfrom(self, address, count):
        buf = bytearray(count)
        with self._with_lock():
            # CircuitPython API: readfrom_into(address, buffer, *, start=0, end=None, stop=True)
            self._ch.readfrom_into(address, buf)
        return buf

class IOMod:
    """
    IOMod class for managing multiple I/O expander modules through a TCA9548A
    multiplexer, auto-detecting the expander chip on each module
    """
    
    def __init__(self):
        """Initialize the IOMod system"""
        self.tca = None
        self.modules = {}  # Cache for initialized modules
        self.current_module = None
        self._initialized = False
        
    def init(self, i2c_bus=None):
        """
        Initialize the I2C bus and TCA9548A multiplexer
        
        Args:
            i2c_bus: Optional I2C bus object. If None, uses board.I2C()
        """
        try:
            if i2c_bus is None:
                i2c_bus = board.I2C()
            
            # Create the TCA9548A object
            self.tca = adafruit_tca9548a.TCA9548A(i2c_bus)
            self._initialized = True
            print("IOMod system initialized successfully")
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize IOMod system: {e}")
    
    def _validate_module_id(self, module_id):
        """
        Validate a module identifier and normalize it to a numeric channel index (0-7)

        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
        """
        module_id = _module_index(module_id)
        if not 0 <= module_id <= 7:
            raise ValueError(f"Invalid module ID {module_id}. Must be 0-7 (or letter A-H).")
        return module_id
    
    def _validate_pin(self, pin):
        """Validate pin number is within valid range (0-7)"""
        if not 0 <= pin <= 7:
            raise ValueError(f"Invalid pin {pin}. Must be 0-7.")
        return pin
    
    def _get_module(self, module_id):
        """
        Get or create the expander driver instance for the specified module ID.
        The expander chip is identified automatically from the I2C address(es)
        found on the module's multiplexer channel.

        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)

        Returns:
            ExpanderDriver: Configured driver instance for the module
        """
        module_id = self._validate_module_id(module_id)

        if not self._initialized:
            raise RuntimeError("IOMod system not initialized. Call init() first.")

        # Return cached module if available
        if module_id in self.modules:
            return self.modules[module_id]

        # Wrap the TCA channel with an adapter exposing readfrom/writeto
        channel_adapter = ChannelI2CAdapter(self.tca[module_id])
        addresses = channel_adapter.scan()
        driver_cls, address = identify_driver(channel_adapter, addresses)
        if driver_cls is None:
            raise RuntimeError(f"No supported I/O expander found on module {_module_letter(module_id)}")

        try:
            driver = driver_cls(channel_adapter, address)
            self.modules[module_id] = driver
            print(f"Module {_module_letter(module_id)}: {driver_cls.NAME} initialized successfully")
            return driver
        except Exception as e:
            raise RuntimeError(f"Failed to initialize module {_module_letter(module_id)}: {e}")
    
    def select_module(self, module_id):
        """
        Select a specific module for operations

        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
        """
        module_id = self._validate_module_id(module_id)
        self.current_module = self._get_module(module_id)
        print(f"Selected module {_module_letter(module_id)}")
    
    def digitalwrite(self, module_id, pin, value):
        """
        Write a digital value to a pin on the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            pin (int): Pin number (0-7)
            value (int): HIGH (1) or LOW (0)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)

        # Configure pin as output and write the value
        module.digital_write(pin, value)
        print(f"Module {_module_letter(module_id)}, Pin {pin}: driving {'HIGH' if value else 'LOW'}")
    
    def digitalread(self, module_id, pin):
        """
        Read a digital value from a pin on the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            pin (int): Pin number (0-7)
            
        Returns:
            int: HIGH (1) or LOW (0)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)

        # Configure pin as input and read the value
        value = module.digital_read(pin)
        print(f"Module {_module_letter(module_id)}, Pin {pin}: reading {'HIGH' if value else 'LOW'}")
        return value
    
    def analogread(self, module_id, pin, average=1):
        """
        Read an analog value from a pin on the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            pin (int): Pin number (0-7)
            average (int): Number of samples to average (default: 1)
            
        Returns:
            int: Raw ADC value (0-4095)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)

        # Configure pin as ADC and read the value
        value = module.analog_read(pin, average)
        print(f"Module {_module_letter(module_id)}, Pin {pin}: ADC = {value}")
        return value

    def setLDACMode(self, module_id, mode):
        module = self._get_module(module_id)
        module.set_ldac_mode(mode)
    
    def analogwrite(self, module_id, pin, value):
        """
        Write an analog value to a pin on the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            pin (int): Pin number (0-7)
            value (int): DAC value (0-4095)
            range (int): DAC range setting (1 = Vref, 2 = 2x Vref, default: 2)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)

        # Write the value
        module.analog_write(pin, value)
        print(f"Module {_module_letter(module_id)}, Pin {pin}: DAC = {value}")
    
    def readvoltage(self, module_id, pin, average=1):
        """
        Read voltage from a pin on the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            pin (int): Pin number (0-7)
            average (int): Number of samples to average (default: 1)
            
        Returns:
            float: Voltage value in volts
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)

        # Configure pin as ADC and read the voltage
        voltage = module.read_voltage(pin, average)
        print(f"Module {_module_letter(module_id)}, Pin {pin}: {voltage:.3f}V")
        return voltage
    
    def pinmode(self, module_id, pin, mode):
        """
        Configure pin mode on the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            pin (int): Pin number (0-7)
            mode (int): Pin mode (INPUT, OUTPUT, ADC, or DAC)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)
        module.pin_mode(pin, mode)

        mode_names = {INPUT: "INPUT", OUTPUT: "OUTPUT", ADC: "ADC", DAC: "DAC"}
        print(f"Module {_module_letter(module_id)}, Pin {pin}: Configured as {mode_names[mode]}")
    
    def setvref(self, module_id, activate=True):
        """
        Enable or disable voltage reference for the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            activate (bool): True to enable, False to disable
        """
        module_id = self._validate_module_id(module_id)
        module = self._get_module(module_id)
        module.set_vref(activate)
        print(f"Module {_module_letter(module_id)}: Vref {'enabled' if activate else 'disabled'}")
    
    def getvref(self, module_id):
        """
        Get voltage reference value for the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            
        Returns:
            float: Reference voltage in volts
        """
        module_id = self._validate_module_id(module_id)
        module = self._get_module(module_id)
        vref = module.get_vref()
        print(f"Module {_module_letter(module_id)}: Vref = {vref:.2f}V")
        return vref
    
    def getdacrange(self, module_id):
        """
        Get DAC range setting for the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            
        Returns:
            int: DAC range (1 = 1x Vref, 2 = 2x Vref)
        """
        module_id = self._validate_module_id(module_id)
        module = self._get_module(module_id)
        dac_range = module.get_dac_range()
        print(f"Module {_module_letter(module_id)}: DAC range = {dac_range}x Vref")
        return dac_range
    
    def setdacrange(self, module_id, range=2):
        """
        Set DAC range for the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            range (int): DAC range setting (1 = Vref, 2 = 2x Vref, default: 2)
        """
        module_id = self._validate_module_id(module_id)
        module = self._get_module(module_id)
        module.set_dac_range(range)
        print(f"Module {_module_letter(module_id)}: DAC range set to {'2x Vref' if range == 2 else 'Vref'}")

    def reset_module(self, module_id):
        """
        Reset the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
        """
        module_id = self._validate_module_id(module_id)
        module = self._get_module(module_id)
        module.reset()
        print(f"Module {_module_letter(module_id)}: Reset")
    
    def toggle(self, module_id, pin):
        """
        Toggle a digital output pin on the specified module
        
        Args:
            module_id: Module letter ('A'-'H', preferred) or numeric channel (0-7)
            pin (int): Pin number (0-7)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)

        # Configure pin as output and toggle it
        module.toggle(pin)
        print(f"Module {_module_letter(module_id)}, Pin {pin}: Toggled")
    
    def scan_modules(self):
        """
        Scan for available modules and return a list of working module letters

        Returns:
            list: List of available module letters ('A'-'H')
        """
        if not self._initialized:
            raise RuntimeError("IOMod system not initialized. Call init() first.")

        available_modules = []

        for module_id in range(8):
            try:
                channel_adapter = ChannelI2CAdapter(self.tca[module_id])
                addresses = channel_adapter.scan()
                driver_cls, _address = identify_driver(channel_adapter, addresses)
                if driver_cls is not None:
                    available_modules.append(_module_letter(module_id))
            except Exception:
                # Module not available or error
                pass

        print(f"Available modules: {available_modules}")
        return available_modules

# Global instance for easy access
_iomod = IOMod()

# Convenience functions that use the global instance
def init(i2c_bus=None):
    """Initialize the IOMod system"""
    _iomod.init(i2c_bus)

def digitalwrite(module_id, pin, value):
    """Write a digital value to a pin on the specified module"""
    _iomod.digitalwrite(module_id, pin, value)

def digitalread(module_id, pin):
    """Read a digital value from a pin on the specified module"""
    return _iomod.digitalread(module_id, pin)

def analogread(module_id, pin, average=1):
    """Read an analog value from a pin on the specified module"""
    return _iomod.analogread(module_id, pin, average)

def setLDACMode(module_id, mode):
    _iomod.setLDACMode(module_id, mode)

def analogwrite(module_id, pin, value):
    """Write an analog value to a pin on the specified module"""
    _iomod.analogwrite(module_id, pin, value)

def readvoltage(module_id, pin, average=1):
    """Read voltage from a pin on the specified module"""
    return _iomod.readvoltage(module_id, pin, average)

def pinmode(module_id, pin, mode):
    """Configure pin mode on the specified module"""
    _iomod.pinmode(module_id, pin, mode)

def setvref(module_id, activate=True):
    """Enable or disable voltage reference for the specified module"""
    _iomod.setvref(module_id, activate)

def getvref(module_id):
    """Get voltage reference value for the specified module"""
    return _iomod.getvref(module_id)

def getdacrange(module_id):
    """Get DAC range setting for the specified module"""
    return _iomod.getdacrange(module_id)

def setdacrange(module_id, range=2):
    """Set DAC range for the specified module"""
    _iomod.setdacrange(module_id, range)

def reset_module(module_id):
    """Reset the specified module"""
    _iomod.reset_module(module_id)

def toggle(module_id, pin):
    """Toggle a digital output pin on the specified module"""
    _iomod.toggle(module_id, pin)

def scan_modules():
    """Scan for available modules and return a list of working module letters"""
    return _iomod.scan_modules()

def select_module(module_id):
    """Select a specific module for operations"""
    _iomod.select_module(module_id)

# Example usage
if __name__ == "__main__":
    # Example usage of the IOMod library
    try:
        # Initialize the system
        init()
        
        # Scan for available modules
        available = scan_modules()
        print(f"Found {len(available)} available modules")
        
        if available:
            # Use the first available module
            module_id = available[0]
            
            # Set pin 2 as output and write HIGH
            digitalwrite(module_id, 2, HIGH)
            
            # Set pin 1 as input and read it
            pinmode(module_id, 1, INPUT)
            value = digitalread(module_id, 1)
            
            # Set pin 3 as ADC and read voltage
            pinmode(module_id, 3, ADC)
            voltage = readvoltage(module_id, 3)
            
            print("Example completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

