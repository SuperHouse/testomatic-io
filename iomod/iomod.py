#!/usr/bin/env python3
"""
IOMod Library - Wrapper for AD5593R with TCA9548A Multiplexer Support

This library provides a high-level interface for controlling multiple AD5593R modules
through a TCA9548A I2C multiplexer. It allows you to select a specific module and
then perform digital/analog operations on that module.

Usage example:
    import iomod_library as iomod
    
    # Initialize the IOMod system
    iomod.init()
    
    # Select module 3 and write HIGH to pin 4
    iomod.digitalwrite(3, 4, iomod.HIGH)
    
    # Select module 2 and read from pin 1
    value = iomod.digitalread(2, 1)
    
    # Select module 1 and read analog value from pin 3
    voltage = iomod.analogread(1, 3)
"""

import board
import adafruit_tca9548a
from ad5593r import AD5593R

# Constants for digital states
HIGH = 1
LOW  = 0

# Constants for pin modes
INPUT  = 1
OUTPUT = 2
ADC  = 3
DAC  = 4

class ChannelI2CAdapter:
    """
    Adapter to provide readfrom/writeto/scan API expected by AD5593R over a
    CircuitPython TCA9548A channel, which exposes readfrom_into/writeto.
    Each call acquires/releases the I2C lock to be safe across operations.
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
    IOMod class for managing multiple AD5593R modules through TCA9548A multiplexer
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
        """Validate module ID is within valid range (0-7)"""
        if not 0 <= module_id <= 7:
            raise ValueError(f"Invalid module ID {module_id}. Must be 0-7.")
        return module_id
    
    def _validate_pin(self, pin):
        """Validate pin number is within valid range (0-7)"""
        if not 0 <= pin <= 7:
            raise ValueError(f"Invalid pin {pin}. Must be 0-7.")
        return pin
    
    def _get_module(self, module_id):
        """
        Get or create AD5593R module instance for the specified module ID
        
        Args:
            module_id (int): Module ID (0-7)
            
        Returns:
            AD5593R: Configured AD5593R instance for the module
        """
        module_id = self._validate_module_id(module_id)
        
        if not self._initialized:
            raise RuntimeError("IOMod system not initialized. Call init() first.")
        
        # Return cached module if available
        if module_id in self.modules:
            return self.modules[module_id]
        
        try:
            # Wrap the TCA channel with an adapter exposing readfrom/writeto
            channel_adapter = ChannelI2CAdapter(self.tca[module_id])
            # Create AD5593R instance for this channel
            ad5593r = AD5593R(channel_adapter, address=0x10)
            self.modules[module_id] = ad5593r
            print(f"Module {module_id} initialized successfully")
            return ad5593r
        except Exception as e:
            raise RuntimeError(f"Failed to initialize module {module_id}: {e}")
    
    def select_module(self, module_id):
        """
        Select a specific module for operations
        
        Args:
            module_id (int): Module ID to select (0-7)
        """
        self.current_module = self._get_module(module_id)
        print(f"Selected module {module_id}")
    
    def digitalwrite(self, module_id, pin, value):
        """
        Write a digital value to a pin on the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            pin (int): Pin number (0-7)
            value (int): HIGH (1) or LOW (0)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)
        
        # Configure pin as output if not already
        module.OUTPUT(pin)
        
        # Write the value
        module.digitalWrite(pin, value)
        print(f"Module {module_id}, Pin {pin}: driving {'HIGH' if value else 'LOW'}")
    
    def digitalread(self, module_id, pin):
        """
        Read a digital value from a pin on the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            pin (int): Pin number (0-7)
            
        Returns:
            int: HIGH (1) or LOW (0)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)
        
        # Configure pin as input if not already
        module.INPUT(pin)
        
        # Read the value
        value = module.digitalRead(pin)
        print(f"Module {module_id}, Pin {pin}: reading {'HIGH' if value else 'LOW'}")
        return value
    
    def analogread(self, module_id, pin, average=1):
        """
        Read an analog value from a pin on the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            pin (int): Pin number (0-7)
            average (int): Number of samples to average (default: 1)
            
        Returns:
            int: Raw ADC value (0-4095)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)
        
        # Configure pin as ADC if not already
        module.ADC(pin)
        
        # Read the value
        value = module.analogRead(pin, average)
        print(f"Module {module_id}, Pin {pin}: ADC = {value}")
        return value

    def setLDACMode(self, module_id, mode):
        module = self._get_module(module_id)
        module.setLDACMode(mode)
    
    def analogwrite(self, module_id, pin, value):
        """
        Write an analog value to a pin on the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            pin (int): Pin number (0-7)
            value (int): DAC value (0-4095)
            range (int): DAC range setting (1 = Vref, 2 = 2x Vref, default: 2)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)
        
        # Write the value (this will also configure the pin as DAC with the specified range)
        module.analogWrite(pin, value)
        print(f"Module {module_id}, Pin {pin}: DAC = {value}")
    
    def readvoltage(self, module_id, pin, average=1):
        """
        Read voltage from a pin on the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            pin (int): Pin number (0-7)
            average (int): Number of samples to average (default: 1)
            
        Returns:
            float: Voltage value in volts
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)
        
        # Configure pin as ADC if not already
        module.ADC(pin)
        
        # Read the voltage
        voltage = module.readVoltage(pin, average)
        print(f"Module {module_id}, Pin {pin}: {voltage:.3f}V")
        return voltage
    
    def pinmode(self, module_id, pin, mode):
        """
        Configure pin mode on the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            pin (int): Pin number (0-7)
            mode (int): Pin mode (INPUT, OUTPUT, ADC, or DAC)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)
        
        if mode == INPUT:
            module.INPUT(pin)
            print(f"Module {module_id}, Pin {pin}: Configured as INPUT")
        elif mode == OUTPUT:
            module.OUTPUT(pin)
            print(f"Module {module_id}, Pin {pin}: Configured as OUTPUT")
        elif mode == ADC:
            module.ADC(pin)
            print(f"Module {module_id}, Pin {pin}: Configured as ADC")
        elif mode == DAC:
            module.DAC(pin)
            print(f"Module {module_id}, Pin {pin}: Configured as DAC")
        else:
            raise ValueError(f"Invalid pin mode {mode}. Use INPUT, OUTPUT, ADC, or DAC.")
    
    def setvref(self, module_id, activate=True):
        """
        Enable or disable voltage reference for the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            activate (bool): True to enable, False to disable
        """
        module_id = self._validate_module_id(module_id)
        module = self._get_module(module_id)
        module.setVref(activate)
        print(f"Module {module_id}: Vref {'enabled' if activate else 'disabled'}")
    
    def getvref(self, module_id):
        """
        Get voltage reference value for the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            
        Returns:
            float: Reference voltage in volts
        """
        module_id = self._validate_module_id(module_id)
        module = self._get_module(module_id)
        vref = module.getVref()
        print(f"Module {module_id}: Vref = {vref:.2f}V")
        return vref
    
    def getdacrange(self, module_id):
        """
        Get DAC range setting for the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            
        Returns:
            int: DAC range (1 = 1x Vref, 2 = 2x Vref)
        """
        module_id = self._validate_module_id(module_id)
        module = self._get_module(module_id)
        dac_range = module.getDACRange()
        print(f"Module {module_id}: DAC range = {dac_range}x Vref")
        return dac_range
    
    def setdacrange(self, module_id, range=2):
        """
        Set DAC range for the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            range (int): DAC range setting (1 = Vref, 2 = 2x Vref, default: 2)
        """
        module_id = self._validate_module_id(module_id)
        module = self._get_module(module_id)
        module.setDACRange(range)
        print(f"Module {module_id}: DAC range set to {'2x Vref' if range == 2 else 'Vref'}")

    def reset_module(self, module_id):
        """
        Reset the specified module
        
        Args:
            module_id (int): Module ID (0-7)
        """
        module_id = self._validate_module_id(module_id)
        module = self._get_module(module_id)
        module.reset()
        print(f"Module {module_id}: Reset")
    
    def toggle(self, module_id, pin):
        """
        Toggle a digital output pin on the specified module
        
        Args:
            module_id (int): Module ID (0-7)
            pin (int): Pin number (0-7)
        """
        module_id = self._validate_module_id(module_id)
        pin = self._validate_pin(pin)
        
        module = self._get_module(module_id)
        
        # Configure pin as output if not already
        module.OUTPUT(pin)
        
        # Toggle the pin
        module.toggle(pin)
        print(f"Module {module_id}, Pin {pin}: Toggled")
    
    def scan_modules(self):
        """
        Scan for available modules and return a list of working module IDs
        
        Returns:
            list: List of available module IDs
        """
        if not self._initialized:
            raise RuntimeError("IOMod system not initialized. Call init() first.")
        
        available_modules = []
        
        for module_id in range(8):
            try:
                channel_adapter = ChannelI2CAdapter(self.tca[module_id])
                # Try to create AD5593R instance
                _ = AD5593R(channel_adapter, address=0x10)
                available_modules.append(module_id)
            except:
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
    """Scan for available modules and return a list of working module IDs"""
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

